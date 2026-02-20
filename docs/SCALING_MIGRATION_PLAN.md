# Trading Analyzer: Multi-Tenant Scaling Migration Plan

## Executive Summary

This document outlines the **minimum viable migration** from a single-user desktop application to a multi-tenant platform supporting 10,000+ users, deployed on **FreeBSD with jails**.

**Current State:** Single-user SQLite-based desktop app with FastAPI backend  
**Target State:** Multi-tenant SaaS on FreeBSD with PostgreSQL, Clerk authentication, and jail-based isolation

---

## Minimum Requirements Overview

These are the **essential changes** required for multi-tenant scaling. Everything else is optimization.

| Requirement | Why Essential | Deferrable? |
|-------------|---------------|-------------|
| Authentication (Clerk) | Users need accounts | ❌ No |
| User isolation in DB | Data privacy/security | ❌ No |
| PostgreSQL migration | SQLite can't handle concurrent writes | ❌ No |
| Async database driver | Blocking calls kill throughput | ❌ No |
| Rate limiting | Prevent abuse | ⚠️ Can be basic |
| Input validation | Security | ⚠️ Can be basic |
| HTTPS | Security | ❌ No |
| Redis caching | Performance | ✅ Yes (Phase 2) |
| Auto-scaling | Handle load spikes | ✅ Yes (Phase 2) |
| Advanced monitoring | Observability | ✅ Yes (Phase 2) |

---

## Why Clerk for Authentication?

| Aspect | Custom JWT | Clerk |
|--------|-----------|-------|
| **User storage** | Your DB | Managed |
| **Password hashing** | You implement | Managed |
| **Email verification** | You implement | Managed |
| **Password reset** | You implement | Managed |
| **MFA/2FA** | You implement | Built-in |
| **OAuth (Google, GitHub)** | Complex | 1 click |
| **Brute force protection** | You implement | Built-in |
| **Code to write** | ~500-800 lines | ~50 lines |
| **Security liability** | You | Clerk |
| **Cost (10k MAU)** | $0 | Free (under limit) |

**Clerk is free for up to 10,000 monthly active users.**

---

## Phase 1: Core Multi-Tenancy (Minimum Viable)

**Duration:** 2-3 weeks  
**Goal:** Multiple users can securely use the application with isolated data

### 1.1 Clerk Setup

1. Create account at [clerk.com](https://clerk.com)
2. Create application
3. Enable desired auth methods (email, Google, GitHub, etc.)
4. Get API keys:
   - `CLERK_PUBLISHABLE_KEY` (frontend)
   - `CLERK_SECRET_KEY` (backend, if needed)
   - `CLERK_DOMAIN` (e.g., `your-app.clerk.accounts.dev`)

### 1.2 Database Schema Changes

With Clerk, we don't need a users table for authentication. We store the Clerk user ID as a foreign key:

```sql
-- NO users table needed - Clerk manages user data

-- Accounts table references Clerk user ID
CREATE TABLE accounts (
    account_id SERIAL PRIMARY KEY,
    clerk_user_id VARCHAR(255) NOT NULL,  -- e.g., "user_2NNEqL2nrIRdJ194ndJqAHwEfxC"
    account_name VARCHAR(100),
    broker_name VARCHAR(100),
    currency VARCHAR(3) NOT NULL,
    initial_balance DECIMAL(15, 2) DEFAULT 0,
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_accounts_clerk_user_id ON accounts(clerk_user_id);

-- User settings (keyed by Clerk user ID)
CREATE TABLE user_settings (
    clerk_user_id VARCHAR(255) PRIMARY KEY,
    default_currency VARCHAR(3) NOT NULL DEFAULT 'USD',
    show_converted BOOLEAN DEFAULT TRUE,
    timezone VARCHAR(50) DEFAULT 'UTC',
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for common queries
CREATE INDEX idx_transactions_account_id ON broker_transactions(account_id);
CREATE INDEX idx_transactions_date ON broker_transactions(transaction_date);
CREATE INDEX idx_transactions_account_date ON broker_transactions(account_id, transaction_date DESC);
```

### 1.3 Backend: Clerk Token Verification

Create a single dependency to verify Clerk JWTs:

```python
# src/api/auth/clerk.py
import httpx
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, jwk
from functools import lru_cache
import os

CLERK_DOMAIN = os.environ["CLERK_DOMAIN"]
CLERK_ISSUER = f"https://{CLERK_DOMAIN}"
CLERK_JWKS_URL = f"{CLERK_ISSUER}/.well-known/jwks.json"

security = HTTPBearer()

@lru_cache(maxsize=1)
def get_jwks() -> dict:
    """Fetch and cache Clerk's public keys (JWKS)."""
    response = httpx.get(CLERK_JWKS_URL, timeout=10)
    response.raise_for_status()
    return response.json()

def verify_clerk_token(token: str) -> dict:
    """Verify JWT signed by Clerk and return payload."""
    try:
        jwks = get_jwks()
        unverified_header = jwt.get_unverified_header(token)
    except Exception as e:
        raise HTTPException(401, f"Token verification failed: {e}")
    
    # Find the signing key
    key = None
    for k in jwks.get("keys", []):
        if k.get("kid") == unverified_header.get("kid"):
            key = jwk.construct(k)
            break
    
    if not key:
        # Clear cache and retry once (key rotation)
        get_jwks.cache_clear()
        jwks = get_jwks()
        for k in jwks.get("keys", []):
            if k.get("kid") == unverified_header.get("kid"):
                key = jwk.construct(k)
                break
    
    if not key:
        raise HTTPException(401, "Invalid token signing key")
    
    try:
        payload = jwt.decode(
            token,
            key.to_pem(),
            algorithms=["RS256"],
            issuer=CLERK_ISSUER,
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Token expired")
    except jwt.JWTError as e:
        raise HTTPException(401, f"Invalid token: {e}")

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> str:
    """
    FastAPI dependency that extracts and validates the Clerk user ID.
    
    Returns:
        str: Clerk user ID (e.g., "user_2NNEqL2nrIRdJ194ndJqAHwEfxC")
    
    Raises:
        HTTPException 401: If token is missing, invalid, or expired
    """
    payload = verify_clerk_token(credentials.credentials)
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(401, "Invalid token: missing user ID")
    return user_id
```

### 1.4 Backend: Protect All Routes

Every router endpoint must use the `get_current_user` dependency:

```python
# src/api/routers/dashboard.py
from api.auth.clerk import get_current_user

@router.get("/dashboard")
async def get_dashboard(
    currency: str = Query(..., description="Target currency (required)"),
    user_id: str = Depends(get_current_user),  # Clerk user ID
    db: AsyncSession = Depends(get_db),
):
    """Get dashboard data for the authenticated user."""
    kpis = await get_kpi_metrics(db, user_id=user_id, target_currency=currency)
    # ... rest of implementation
```

### 1.5 Backend: PostgreSQL with Async Driver

```python
# src/api/database/connection.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
import os

DATABASE_URL = os.environ["DATABASE_URL"]  # postgresql+asyncpg://...

engine = create_async_engine(
    DATABASE_URL,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,
)

AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def get_db():
    """FastAPI dependency for database sessions."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
```

### 1.6 Backend: User-Isolated Queries

All database queries must filter by `clerk_user_id`:

```python
# src/api/services/database.py
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

async def get_all_trades(
    db: AsyncSession,
    user_id: str,  # Clerk user ID
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[dict]:
    """Get trades for a specific user."""
    query = """
        SELECT t.* FROM broker_transactions t
        JOIN accounts a ON t.account_id = a.account_id
        WHERE a.clerk_user_id = :user_id
    """
    params = {"user_id": user_id}
    
    if start_date:
        query += " AND t.transaction_date >= :start_date"
        params["start_date"] = start_date
    
    if end_date:
        query += " AND t.transaction_date <= :end_date"
        params["end_date"] = end_date
    
    query += " ORDER BY t.transaction_date DESC LIMIT :limit OFFSET :offset"
    params["limit"] = limit
    params["offset"] = offset
    
    result = await db.execute(text(query), params)
    return [dict(row._mapping) for row in result.fetchall()]

async def get_user_accounts(db: AsyncSession, user_id: str) -> list[dict]:
    """Get all accounts for a specific user."""
    query = """
        SELECT * FROM accounts 
        WHERE clerk_user_id = :user_id
        ORDER BY account_name
    """
    result = await db.execute(text(query), {"user_id": user_id})
    return [dict(row._mapping) for row in result.fetchall()]

async def create_account(
    db: AsyncSession,
    user_id: str,
    account_name: str,
    broker_name: str,
    currency: str,
) -> dict:
    """Create a new account for a user."""
    query = """
        INSERT INTO accounts (clerk_user_id, account_name, broker_name, currency)
        VALUES (:user_id, :account_name, :broker_name, :currency)
        RETURNING *
    """
    result = await db.execute(text(query), {
        "user_id": user_id,
        "account_name": account_name,
        "broker_name": broker_name,
        "currency": currency,
    })
    return dict(result.fetchone()._mapping)
```

### 1.7 Frontend: Clerk Integration (Next.js)

Install Clerk:
```bash
npm install @clerk/nextjs
```

Configure environment:
```bash
# frontend/.env.local
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_...
CLERK_SECRET_KEY=sk_test_...
NEXT_PUBLIC_CLERK_SIGN_IN_URL=/sign-in
NEXT_PUBLIC_CLERK_SIGN_UP_URL=/sign-up
NEXT_PUBLIC_CLERK_AFTER_SIGN_IN_URL=/
NEXT_PUBLIC_CLERK_AFTER_SIGN_UP_URL=/
```

Wrap app with ClerkProvider:
```typescript
// frontend/src/app/layout.tsx
import { ClerkProvider } from '@clerk/nextjs';

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <ClerkProvider>
      <html lang="en">
        <body>{children}</body>
      </html>
    </ClerkProvider>
  );
}
```

Add sign-in page (Clerk's hosted UI):
```typescript
// frontend/src/app/sign-in/[[...sign-in]]/page.tsx
import { SignIn } from '@clerk/nextjs';

export default function SignInPage() {
  return (
    <div className="flex min-h-screen items-center justify-center">
      <SignIn />
    </div>
  );
}
```

Add sign-up page:
```typescript
// frontend/src/app/sign-up/[[...sign-up]]/page.tsx
import { SignUp } from '@clerk/nextjs';

export default function SignUpPage() {
  return (
    <div className="flex min-h-screen items-center justify-center">
      <SignUp />
    </div>
  );
}
```

Protect routes with middleware:
```typescript
// frontend/src/middleware.ts
import { clerkMiddleware, createRouteMatcher } from '@clerk/nextjs/server';

const isPublicRoute = createRouteMatcher(['/sign-in(.*)', '/sign-up(.*)']);

export default clerkMiddleware((auth, request) => {
  if (!isPublicRoute(request)) {
    auth().protect();
  }
});

export const config = {
  matcher: ['/((?!.*\\..*|_next).*)', '/', '/(api|trpc)(.*)'],
};
```

### 1.8 Frontend: API Client with Clerk Auth

```typescript
// frontend/src/lib/api.ts
import { useAuth } from '@clerk/nextjs';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || '';

export function useApiClient() {
  const { getToken, isSignedIn } = useAuth();

  async function fetchWithAuth<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    if (!isSignedIn) {
      throw new Error('Not authenticated');
    }

    const token = await getToken();
    
    const response = await fetch(`${API_BASE}${endpoint}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
        Authorization: `Bearer ${token}`,
      },
    });

    if (!response.ok) {
      if (response.status === 401) {
        // Token expired or invalid - Clerk will handle refresh
        throw new Error('Authentication failed');
      }
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || `API error: ${response.status}`);
    }

    return response.json();
  }

  return { fetchWithAuth, isSignedIn };
}

// Typed API functions
export function useApi() {
  const { fetchWithAuth } = useApiClient();

  return {
    getDashboard: (currency: string) =>
      fetchWithAuth<DashboardData>(`/api/dashboard?currency=${currency}`),

    getAccounts: () =>
      fetchWithAuth<Account[]>('/api/accounts'),

    getTrades: (params: TradeParams) => {
      const query = new URLSearchParams();
      query.set('currency', params.currency);
      if (params.from) query.set('from', params.from.toISOString());
      if (params.to) query.set('to', params.to.toISOString());
      if (params.limit) query.set('limit', params.limit.toString());
      return fetchWithAuth<Trade[]>(`/api/trades?${query}`);
    },

    uploadCsv: (accountId: number, file: File) => {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('account_id', accountId.toString());
      return fetchWithAuth<ImportResult>('/api/import/upload', {
        method: 'POST',
        headers: {}, // Let browser set Content-Type for FormData
        body: formData,
      });
    },
  };
}
```

### 1.9 Frontend: User Menu Component

```typescript
// frontend/src/components/UserMenu.tsx
import { UserButton, useUser } from '@clerk/nextjs';

export function UserMenu() {
  const { user, isLoaded } = useUser();

  if (!isLoaded) {
    return <div className="h-8 w-8 animate-pulse rounded-full bg-gray-200" />;
  }

  return (
    <div className="flex items-center gap-3">
      <span className="text-sm text-gray-600">
        {user?.primaryEmailAddress?.emailAddress}
      </span>
      <UserButton afterSignOutUrl="/sign-in" />
    </div>
  );
}
```

### 1.10 Basic Security (Minimum)

**Rate limiting (simple in-memory for start):**

```python
# src/api/middleware/rate_limit.py
from collections import defaultdict
from time import time
from fastapi import HTTPException, Request

request_counts: dict[str, list[float]] = defaultdict(list)
RATE_LIMIT = 100  # requests per minute

async def rate_limit_middleware(request: Request, call_next):
    client_ip = request.client.host if request.client else "unknown"
    now = time()
    minute_ago = now - 60
    
    # Clean old requests
    request_counts[client_ip] = [t for t in request_counts[client_ip] if t > minute_ago]
    
    if len(request_counts[client_ip]) >= RATE_LIMIT:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    request_counts[client_ip].append(now)
    return await call_next(request)
```

**Input validation for CSV upload:**

```python
# src/api/validators.py
from fastapi import HTTPException, UploadFile

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
MAX_ROWS = 100_000

async def validate_csv(file: UploadFile) -> bytes:
    content = await file.read()
    
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(400, "File too large (max 10MB)")
    
    if not file.filename or not file.filename.endswith('.csv'):
        raise HTTPException(400, "Only CSV files allowed")
    
    row_count = content.count(b'\n')
    if row_count > MAX_ROWS:
        raise HTTPException(400, f"Too many rows (max {MAX_ROWS})")
    
    return content
```

### 1.11 Phase 1 Deliverables Checklist

- [ ] Clerk account and application created
- [ ] PostgreSQL schema with `clerk_user_id` columns
- [ ] Clerk token verification dependency (`get_current_user`)
- [ ] All routes protected with `Depends(get_current_user)`
- [ ] All queries filtered by `clerk_user_id`
- [ ] Async database driver (asyncpg)
- [ ] Basic rate limiting middleware
- [ ] CSV upload validation
- [ ] Frontend ClerkProvider setup
- [ ] Frontend sign-in/sign-up pages
- [ ] Frontend middleware for route protection
- [ ] Frontend API client with Clerk auth
- [ ] User menu component with sign-out

---

## Phase 2: Production Hardening (After Launch)

**Duration:** 2-3 weeks  
**Goal:** Performance and reliability improvements

### 2.1 Redis Caching

Add caching for expensive queries after validating the system works.

### 2.2 Clerk Webhooks

Sync user data to your database when users are created/updated/deleted:

```python
# src/api/routers/webhooks.py
from fastapi import APIRouter, Request, HTTPException
from svix.webhooks import Webhook, WebhookVerificationError
import os

router = APIRouter()
CLERK_WEBHOOK_SECRET = os.environ["CLERK_WEBHOOK_SECRET"]

@router.post("/clerk")
async def clerk_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    payload = await request.body()
    headers = dict(request.headers)
    
    try:
        wh = Webhook(CLERK_WEBHOOK_SECRET)
        event = wh.verify(payload, headers)
    except WebhookVerificationError:
        raise HTTPException(400, "Invalid webhook signature")
    
    event_type = event.get("type")
    data = event.get("data", {})
    
    if event_type == "user.created":
        # Optionally create default settings
        await db.execute(text("""
            INSERT INTO user_settings (clerk_user_id, default_currency)
            VALUES (:user_id, 'USD')
            ON CONFLICT DO NOTHING
        """), {"user_id": data["id"]})
    
    elif event_type == "user.deleted":
        # Clean up user data (or implement soft delete)
        await db.execute(text("""
            DELETE FROM accounts WHERE clerk_user_id = :user_id
        """), {"user_id": data["id"]})
    
    return {"status": "ok"}
```

### 2.3 Advanced Monitoring

Add Prometheus metrics and alerting.

---

## FreeBSD Jail Architecture

### Why FreeBSD Jails?

| Feature | Docker/Linux | FreeBSD Jails |
|---------|--------------|---------------|
| Isolation | Namespaces | OS-level virtualization |
| Security | Good | Excellent (decades mature) |
| Performance | Near-native | Native |
| Networking | Overlay networks | VNET (native) |
| ZFS integration | External | Native |
| Resource limits | cgroups | rctl |
| Complexity | High (orchestration) | Lower (simpler model) |

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                        FreeBSD Host                                  │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                      pf firewall                             │    │
│  │   (rate limiting, port forwarding, NAT)                     │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                      │
│  ┌──────────────┐                                                   │
│  │   nginx      │                                                   │
│  │   jail       │◄─── HTTPS (443)                                   │
│  │  (TLS term)  │                                                   │
│  └──────┬───────┘                                                   │
│         │                                                            │
│         │ HTTP (8000)                                               │
│         ▼                                                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │   api-1      │  │   api-2      │  │   api-3      │              │
│  │   jail       │  │   jail       │  │   jail       │              │
│  │  (FastAPI)   │  │  (FastAPI)   │  │  (FastAPI)   │              │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘              │
│         │                  │                  │                      │
│         └──────────────────┼──────────────────┘                      │
│                            │                                         │
│                            ▼                                         │
│  ┌─────────────────────────────────────────────────┐                │
│  │                PostgreSQL jail                   │                │
│  │                  (database)                      │                │
│  └─────────────────────────────────────────────────┘                │
│                                                                      │
│  ┌─────────────────────────────────────────────────┐                │
│  │                   ZFS Storage                    │                │
│  │   datasets: /jails, /data/postgres, /data/uploads│                │
│  └─────────────────────────────────────────────────┘                │
└─────────────────────────────────────────────────────────────────────┘

External:
┌─────────────────────────────────────────────────────────────────────┐
│                          Clerk                                       │
│  (Authentication, User Management, OAuth)                           │
└─────────────────────────────────────────────────────────────────────┘
```

### Jail Configuration

**Using bastille for jail management:**

```sh
# Install bastille
pkg install bastille

# Enable bastille and loopback interface for jails
sysrc bastille_enable="YES"
sysrc cloned_interfaces+="lo1"
sysrc ifconfig_lo1_aliases="inet 10.0.0.1/24"

# Enable rctl for resource limits
echo 'kern.racct.enable=1' >> /boot/loader.conf

# Create base template
bastille bootstrap 14.0-RELEASE

# Create PostgreSQL jail
bastille create postgres 14.0-RELEASE 10.0.0.10
bastille pkg postgres install postgresql16-server
bastille sysrc postgres postgresql_enable="YES"
bastille service postgres postgresql initdb
bastille service postgres postgresql start

# Create API jails
for i in 1 2 3; do
    bastille create api-$i 14.0-RELEASE 10.0.0.1$i
    bastille pkg api-$i install python311 py311-pip py311-uvicorn py311-httpx
    bastille cmd api-$i pip install fastapi sqlalchemy asyncpg python-jose
done

# Create nginx jail
bastille create nginx 14.0-RELEASE 10.0.0.2
bastille pkg nginx install nginx
```

### Jail Resource Limits (rctl)

```sh
# /etc/rctl.conf

# API jails: 2GB RAM, 50% CPU each
jail:api-1:memoryuse:deny=2G
jail:api-1:pcpu:deny=50

jail:api-2:memoryuse:deny=2G
jail:api-2:pcpu:deny=50

jail:api-3:memoryuse:deny=2G
jail:api-3:pcpu:deny=50

# PostgreSQL: more resources
jail:postgres:memoryuse:deny=8G
jail:postgres:pcpu:deny=100
```

### pf Firewall Configuration

```
# /etc/pf.conf

# Interfaces
ext_if = "em0"
jail_if = "lo1"

# Jail IPs
nginx_ip = "10.0.0.2"
api_ips = "{ 10.0.0.11, 10.0.0.12, 10.0.0.13 }"
postgres_ip = "10.0.0.10"

# Rate limiting table
table <bruteforce> persist

# Options
set skip on lo0
set block-policy drop

# Normalization
scrub in all

# NAT for jails (outbound)
nat on $ext_if from ($jail_if:network) to any -> ($ext_if)

# Default deny
block all

# Allow SSH with rate limiting
pass in on $ext_if proto tcp to port 22 keep state \
    (max-src-conn 10, max-src-conn-rate 5/60, overload <bruteforce> flush)

# Allow HTTPS
pass in on $ext_if proto tcp to port 443 keep state

# Redirect HTTPS to nginx jail
rdr on $ext_if proto tcp to port 443 -> $nginx_ip port 443

# Internal: nginx -> API jails
pass on $jail_if proto tcp from $nginx_ip to $api_ips port 8000

# Internal: API jails -> PostgreSQL
pass on $jail_if proto tcp from $api_ips to $postgres_ip port 5432

# Internal: API jails -> external (Clerk API)
pass out on $ext_if proto tcp from $api_ips to any port { 80, 443 } keep state

# Allow all outbound from host
pass out on $ext_if proto { tcp, udp } to any keep state
```

### nginx Configuration (in nginx jail)

```nginx
# /usr/local/etc/nginx/nginx.conf

worker_processes auto;
events {
    worker_connections 1024;
}

http {
    include mime.types;
    default_type application/octet-stream;

    # Logging
    access_log /var/log/nginx/access.log;
    error_log /var/log/nginx/error.log;

    # Upstream API servers
    upstream api_servers {
        least_conn;
        server 10.0.0.11:8000 weight=1;
        server 10.0.0.12:8000 weight=1;
        server 10.0.0.13:8000 weight=1;
    }

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;

    server {
        listen 443 ssl http2;
        server_name trading.yourdomain.com;

        # TLS
        ssl_certificate /usr/local/etc/ssl/fullchain.pem;
        ssl_certificate_key /usr/local/etc/ssl/privkey.pem;
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;
        ssl_prefer_server_ciphers on;
        ssl_session_cache shared:SSL:10m;

        # Security headers
        add_header X-Frame-Options "DENY" always;
        add_header X-Content-Type-Options "nosniff" always;
        add_header X-XSS-Protection "1; mode=block" always;
        add_header Strict-Transport-Security "max-age=31536000" always;

        # API proxy
        location /api/ {
            limit_req zone=api burst=20 nodelay;
            
            proxy_pass http://api_servers;
            proxy_http_version 1.1;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_connect_timeout 10s;
            proxy_read_timeout 30s;
        }

        # Static frontend
        location / {
            root /usr/local/www/frontend;
            try_files $uri $uri.html $uri/ /index.html;
            
            # Cache static assets
            location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2)$ {
                expires 1y;
                add_header Cache-Control "public, immutable";
            }
        }
    }

    # Redirect HTTP to HTTPS
    server {
        listen 80;
        server_name trading.yourdomain.com;
        return 301 https://$server_name$request_uri;
    }
}
```

### rc.d Service Script (for each API jail)

```sh
#!/bin/sh
# /usr/local/etc/rc.d/trading_api

# PROVIDE: trading_api
# REQUIRE: LOGIN postgresql
# KEYWORD: shutdown

. /etc/rc.subr

name="trading_api"
rcvar="trading_api_enable"

load_rc_config $name

: ${trading_api_enable:="NO"}
: ${trading_api_user:="www"}
: ${trading_api_dir:="/app"}
: ${trading_api_host:="0.0.0.0"}
: ${trading_api_port:="8000"}
: ${trading_api_workers:="4"}

pidfile="/var/run/${name}.pid"
command="/usr/local/bin/uvicorn"
command_args="api.main:app --host ${trading_api_host} --port ${trading_api_port} --workers ${trading_api_workers}"

start_cmd="${name}_start"
stop_cmd="${name}_stop"
status_cmd="${name}_status"

trading_api_start() {
    echo "Starting ${name}..."
    cd ${trading_api_dir}
    
    # Load environment
    if [ -f ${trading_api_dir}/.env ]; then
        export $(cat ${trading_api_dir}/.env | grep -v '^#' | xargs)
    fi
    
    /usr/sbin/daemon -p ${pidfile} -u ${trading_api_user} \
        ${command} ${command_args}
}

trading_api_stop() {
    if [ -f ${pidfile} ]; then
        echo "Stopping ${name}..."
        kill $(cat ${pidfile}) 2>/dev/null
        rm -f ${pidfile}
    fi
}

trading_api_status() {
    if [ -f ${pidfile} ] && kill -0 $(cat ${pidfile}) 2>/dev/null; then
        echo "${name} is running as pid $(cat ${pidfile})"
    else
        echo "${name} is not running"
        return 1
    fi
}

run_rc_command "$1"
```

### Deployment Script

```sh
#!/bin/sh
# /root/deploy.sh - Deploy new version to API jails

set -e

VERSION=$1
if [ -z "$VERSION" ]; then
    echo "Usage: deploy.sh <version>"
    exit 1
fi

JAILS="api-1 api-2 api-3"
APP_DIR="/app"

echo "Deploying version ${VERSION}..."

for jail in $JAILS; do
    echo "=== Deploying to $jail ==="
    
    # Stop the service
    bastille cmd $jail service trading_api stop || true
    
    # Update code
    bastille cmd $jail git -C $APP_DIR fetch origin
    bastille cmd $jail git -C $APP_DIR checkout $VERSION
    
    # Install dependencies
    bastille cmd $jail pip install -r $APP_DIR/requirements.txt
    
    # Run migrations (only on first jail)
    if [ "$jail" = "api-1" ]; then
        bastille cmd $jail python $APP_DIR/scripts/migrate.py
    fi
    
    # Start service
    bastille cmd $jail service trading_api start
    
    # Health check
    sleep 3
    if bastille cmd $jail curl -sf http://localhost:8000/api/health > /dev/null; then
        echo "$jail: OK"
    else
        echo "$jail: FAILED - rolling back"
        bastille cmd $jail git -C $APP_DIR checkout HEAD~1
        bastille cmd $jail service trading_api restart
        exit 1
    fi
done

echo "=== Deployment complete ==="
```

### ZFS Configuration

```sh
# Create ZFS datasets
zfs create zroot/jails
zfs create zroot/data
zfs create zroot/data/postgres
zfs create zroot/data/uploads

# Optimize for workload
zfs set compression=lz4 zroot/data
zfs set recordsize=8K zroot/data/postgres  # Optimal for PostgreSQL
zfs set atime=off zroot/data

# Automated snapshots (add to cron)
# Daily snapshot at 2 AM
# 0 2 * * * /sbin/zfs snapshot -r zroot/data@daily-$(date +\%Y\%m\%d)
# Delete snapshots older than 7 days at 3 AM
# 0 3 * * * /sbin/zfs list -t snapshot -o name | grep "daily-" | head -n -7 | xargs -n1 zfs destroy
```

### PostgreSQL Configuration (in postgres jail)

```
# /var/db/postgres/data16/postgresql.conf

# Connections
listen_addresses = '10.0.0.10'
max_connections = 100

# Memory (adjust based on available RAM)
shared_buffers = 2GB
effective_cache_size = 6GB
work_mem = 64MB
maintenance_work_mem = 512MB

# WAL
wal_buffers = 64MB
checkpoint_completion_target = 0.9

# Query tuning
random_page_cost = 1.1  # For SSD/NVMe
effective_io_concurrency = 200

# Logging
log_destination = 'syslog'
log_min_duration_statement = 1000  # Log slow queries (>1s)
```

```
# /var/db/postgres/data16/pg_hba.conf

# Local connections
local   all   all                 trust
host    all   all   127.0.0.1/32  trust

# API jails (use scram-sha-256)
host    trading   trading_app   10.0.0.11/32   scram-sha-256
host    trading   trading_app   10.0.0.12/32   scram-sha-256
host    trading   trading_app   10.0.0.13/32   scram-sha-256
```

---

## Environment Variables

```sh
# /app/.env (in each API jail)

# Database
DATABASE_URL=postgresql+asyncpg://trading_app:YOUR_DB_PASSWORD@10.0.0.10/trading

# Clerk
CLERK_DOMAIN=your-app.clerk.accounts.dev

# Security
ALLOWED_ORIGINS=https://trading.yourdomain.com

# Optional (Phase 2)
# CLERK_WEBHOOK_SECRET=whsec_...
# REDIS_URL=redis://10.0.0.20:6379/0
```

---

## Hardware Requirements

### Minimum (up to 1,000 users)

| Component | Specification |
|-----------|---------------|
| CPU | 4 cores |
| RAM | 16 GB |
| Storage | 100 GB NVMe |
| Network | 1 Gbps |

**Jail allocation:**
- nginx: 1 GB RAM
- api-1: 2 GB RAM
- api-2: 2 GB RAM
- postgres: 8 GB RAM
- System: 3 GB RAM

### Recommended (up to 10,000 users)

| Component | Specification |
|-----------|---------------|
| CPU | 8-16 cores |
| RAM | 32-64 GB |
| Storage | 500 GB NVMe |
| Network | 1-10 Gbps |

**Jail allocation:**
- nginx: 2 GB RAM
- api-1, api-2, api-3: 4 GB RAM each
- postgres: 16 GB RAM
- redis (Phase 2): 4 GB RAM
- System: 4-8 GB RAM

---

## Migration Timeline

| Week | Tasks |
|------|-------|
| 1 | Clerk setup, PostgreSQL schema, async database layer |
| 2 | Protect all routes, user-isolated queries, basic security |
| 3 | Frontend Clerk integration, testing, FreeBSD deployment |

**Total: 3 weeks to production-ready minimum**

---

## Monitoring (Simple)

```sh
#!/bin/sh
# /root/healthcheck.sh

# Check API jails
for jail in api-1 api-2 api-3; do
    if ! bastille cmd $jail curl -sf http://localhost:8000/api/health > /dev/null; then
        echo "ALERT: $jail is unhealthy" | mail -s "Health Alert" admin@example.com
    fi
done

# Check PostgreSQL
if ! bastille cmd postgres psql -U postgres -c "SELECT 1" > /dev/null 2>&1; then
    echo "ALERT: PostgreSQL is down" | mail -s "Health Alert" admin@example.com
fi

# Check disk space
DISK_USAGE=$(df -h / | awk 'NR==2 {print int($5)}')
if [ "$DISK_USAGE" -gt 80 ]; then
    echo "ALERT: Disk usage at ${DISK_USAGE}%" | mail -s "Health Alert" admin@example.com
fi
```

Add to cron: `*/5 * * * * /root/healthcheck.sh`

---

## Backup Strategy

```sh
#!/bin/sh
# /root/backup.sh

DATE=$(date +%Y%m%d)
BACKUP_DIR=/backup

# ZFS snapshot
zfs snapshot -r zroot/data@backup-$DATE

# PostgreSQL dump
bastille cmd postgres pg_dump -U postgres trading | gzip > $BACKUP_DIR/postgres-$DATE.sql.gz

# Sync to offsite
rsync -avz $BACKUP_DIR/ backup-server:/backups/trading/

# Cleanup (keep 7 days)
find $BACKUP_DIR -name "*.gz" -mtime +7 -delete
zfs list -t snapshot -o name | grep "backup-" | head -n -7 | xargs -n1 zfs destroy 2>/dev/null
```

---

## Cost Estimation

### Authentication (Clerk)

| Users | Cost |
|-------|------|
| 0 - 10,000 MAU | Free |
| 10,001+ MAU | $0.02/MAU |

### Hosting (Dedicated Server)

| Provider | Spec | Monthly Cost |
|----------|------|--------------|
| Hetzner AX41-NVMe | Ryzen 5 3600, 64GB, 2x512GB NVMe | €50 |
| OVH Rise-1 | Xeon E-2136, 32GB, 2x500GB SSD | €70 |
| Vultr Bare Metal | 8 cores, 32GB, 240GB SSD | $120 |

### Total Monthly Cost (10,000 users)

| Item | Cost |
|------|------|
| Clerk | $0 (free tier) |
| Hetzner AX41-NVMe | €50 (~$55) |
| Domain + SSL (Let's Encrypt) | $0 |
| **Total** | **~$55/month** |

---

## Security Checklist

- [x] Authentication handled by Clerk (battle-tested)
- [x] HTTPS/TLS termination at nginx
- [x] JWT verification on every request
- [x] User data isolation (clerk_user_id filtering)
- [x] Rate limiting at nginx and application level
- [x] Input validation for file uploads
- [x] SQL injection prevention (parameterized queries)
- [x] pf firewall restricting jail communication
- [x] Resource limits preventing jail escape
- [x] ZFS snapshots for data recovery

---

## Questions for Discussion

1. **Clerk Configuration:** Which auth methods to enable? (Email, Google, GitHub, etc.)
2. **Hosting Provider:** Hetzner, OVH, or other?
3. **Domain:** Already have one or need to register?
4. **Backup Destination:** Cloud storage (Backblaze B2, S3) or second server?
5. **Email Notifications:** For alerts - use Clerk's email or separate service?