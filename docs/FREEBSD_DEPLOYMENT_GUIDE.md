# FreeBSD 15.0 Deployment Guide

Complete guide for deploying Trading Analyzer on FreeBSD 15.0 with jails and nginx.

**Authentication Options:**
- **Option A: Simple Auth** - Built-in email/password (good for testing, MVP)
- **Option B: Clerk** - Managed auth service (OAuth, MFA, enterprise features)

## Prerequisites

- FreeBSD 15.0-RELEASE server (4 CPU, 8GB RAM, 50GB disk minimum)
- Root access
- Domain name pointing to server IP
- **If using Clerk:** Clerk account (free at https://clerk.com)

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                    FreeBSD 15.0 Host                                 │
│                                                                      │
│   ┌──────────┐                                                      │
│   │  nginx   │ :443 → api-prod, :8443 → api-dev                     │
│   │  10.0.0.2│                                                      │
│   └────┬─────┘                                                      │
│        │                                                             │
│   ┌────▼─────┐    ┌──────────┐                                      │
│   │ api-prod │    │ api-dev  │                                      │
│   │ 10.0.0.11│    │ 10.0.0.12│                                      │
│   └────┬─────┘    └────┬─────┘                                      │
│        │               │                                             │
│        └───────┬───────┘                                             │
│                │                                                     │
│   ┌────────────▼────────────┐                                       │
│   │  postgres               │                                       │
│   │  10.0.0.10              │                                       │
│   │  - trading_prod (db)    │                                       │
│   │  - trading_dev (db)     │                                       │
│   └─────────────────────────┘                                       │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘

Ports:
  - 443:  Production (https://trading.yourdomain.com)
  - 8443: Development (https://trading.yourdomain.com:8443)
```

---

## Part 1: Authentication Setup

Choose **ONE** of the following options:

- **Option A: Simple Auth** - Skip to [Part 1A](#part-1a-simple-auth-setup)
- **Option B: Clerk** - Skip to [Part 1B](#part-1b-clerk-setup)

---

## Part 1A: Simple Auth Setup

Self-hosted email/password authentication using Argon2 password hashing and JWT tokens.

### 1A.1 Security Features

| Feature | Implementation |
|---------|----------------|
| Password hashing | Argon2 (winner of Password Hashing Competition) |
| Token format | JWT with HS256 |
| Brute force protection | Rate limiting (5 attempts, 15 min lockout) |
| Password requirements | 10+ chars, upper, lower, number |

### 1A.2 Generate Secret Key

```sh
# Generate a secure secret key (save this!)
openssl rand -base64 32
```

Save this key - you'll need it for the API environment file later.

### 1A.3 Database Schema

The simple auth requires a users table. This will be created in Part 5 when initializing the database.

```sql
CREATE TABLE users (
    user_id UUID PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_login TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT TRUE
);

CREATE INDEX idx_users_email ON users(email);

-- Accounts reference user_id
ALTER TABLE accounts ADD COLUMN user_id UUID REFERENCES users(user_id) ON DELETE CASCADE;
CREATE INDEX idx_accounts_user_id ON accounts(user_id);
```

### 1A.4 What's Included vs Not Included

**Included:**
- Secure password hashing (Argon2)
- JWT token authentication
- Rate limiting / brute force protection
- Password strength validation

**Not included (add later if needed):**
- Password reset via email
- Email verification
- MFA/2FA
- OAuth providers (Google, GitHub)

Skip to [Part 2: FreeBSD Host Setup](#part-2-freebsd-host-setup).

---

## Part 1B: Clerk Setup

### 1B.1 Create Clerk Applications

1. Go to https://clerk.com and sign up
2. Create two applications:
   - `trading-analyzer-prod` (Production)
   - `trading-analyzer-dev` (Development)

3. For each application, go to **Configure → Email, Phone, Username** and enable:
   - Email address (required)
   - Optional: Google OAuth, GitHub OAuth

4. Get API keys from **Configure → API Keys**:
   - `CLERK_PUBLISHABLE_KEY` (starts with `pk_`)
   - `CLERK_SECRET_KEY` (starts with `sk_`)
   - Note the Clerk domain (e.g., `your-app.clerk.accounts.dev`)

### 1B.2 Configure Allowed Origins

For each Clerk application, go to **Configure → Paths** and add:

**Production app:**
```
https://trading.yourdomain.com
```

**Development app:**
```
https://trading.yourdomain.com:8443
```

---

## Part 2: FreeBSD Host Setup

### 2.1 Initial System Configuration

```sh
# Update system
freebsd-update fetch install

# Install required packages
pkg install -y bastille git curl

# Enable ZFS if not already enabled
# (Skip if ZFS is already your root filesystem)
```

### 2.2 Network Configuration for Jails

```sh
# Create loopback interface for jail network
sysrc cloned_interfaces+="lo1"
sysrc ifconfig_lo1_aliases="inet 10.0.0.1/24"

# Apply network changes
service netif cloneup

# Verify
ifconfig lo1
# Should show: inet 10.0.0.1 netmask 0xffffff00
```

### 2.3 Enable and Configure Bastille

```sh
# Enable bastille
sysrc bastille_enable="YES"

# Initialize bastille
bastille setup

# Bootstrap FreeBSD 15.0 base
bastille bootstrap 15.0-RELEASE
```

### 2.4 Configure PF Firewall

Create `/etc/pf.conf`:

```
# Interfaces
ext_if = "vtnet0"  # Change to your interface (check with: ifconfig)
jail_if = "lo1"

# Jail IPs
nginx_ip = "10.0.0.2"
api_prod_ip = "10.0.0.11"
api_dev_ip = "10.0.0.12"
postgres_ip = "10.0.0.10"
api_ips = "{ 10.0.0.11, 10.0.0.12 }"

# Rate limiting tables
table <bruteforce> persist

# Options
set skip on lo0
set block-policy drop

# Normalization
scrub in all

# NAT for jails (outbound internet access)
nat on $ext_if from ($jail_if:network) to any -> ($ext_if)

# Default deny
block all

# Allow SSH with brute force protection
pass in on $ext_if proto tcp to port 22 keep state \
    (max-src-conn 10, max-src-conn-rate 5/60, overload <bruteforce> flush)

# Allow HTTPS (443) and dev HTTPS (8443)
pass in on $ext_if proto tcp to port { 443, 8443 } keep state

# Redirect to nginx jail
rdr on $ext_if proto tcp to port 443 -> $nginx_ip port 443
rdr on $ext_if proto tcp to port 8443 -> $nginx_ip port 8443

# Internal: nginx -> API jails
pass on $jail_if proto tcp from $nginx_ip to $api_ips port 8000

# Internal: API jails -> PostgreSQL
pass on $jail_if proto tcp from $api_ips to $postgres_ip port 5432

# Internal: API jails -> external (Clerk API verification)
pass out on $ext_if proto tcp from ($jail_if:network) to any port { 80, 443 } keep state

# Allow all outbound from host
pass out on $ext_if proto { tcp, udp } to any keep state
```

Enable PF:

```sh
# Enable PF
sysrc pf_enable="YES"

# Load PF rules
service pf start

# Verify rules loaded
pfctl -sr
```

---

## Part 3: Create Jails

### 3.1 Create All Jails

```sh
# PostgreSQL jail
bastille create postgres 15.0-RELEASE 10.0.0.10

# API jails
bastille create api-prod 15.0-RELEASE 10.0.0.11
bastille create api-dev 15.0-RELEASE 10.0.0.12

# nginx jail
bastille create nginx 15.0-RELEASE 10.0.0.2

# Verify jails are running
bastille list
```

### 3.2 Configure PostgreSQL Jail

```sh
# Install PostgreSQL
bastille pkg postgres install -y postgresql16-server

# Enable PostgreSQL
bastille sysrc postgres postgresql_enable="YES"

# Initialize database
bastille cmd postgres service postgresql initdb

# Configure PostgreSQL to listen on jail IP
bastille cmd postgres sh -c 'echo "listen_addresses = '\''10.0.0.10'\''" >> /var/db/postgres/data16/postgresql.conf'
bastille cmd postgres sh -c 'echo "max_connections = 50" >> /var/db/postgres/data16/postgresql.conf'
bastille cmd postgres sh -c 'echo "shared_buffers = 512MB" >> /var/db/postgres/data16/postgresql.conf'
bastille cmd postgres sh -c 'echo "effective_cache_size = 1GB" >> /var/db/postgres/data16/postgresql.conf'
bastille cmd postgres sh -c 'echo "work_mem = 16MB" >> /var/db/postgres/data16/postgresql.conf'
bastille cmd postgres sh -c 'echo "log_min_duration_statement = 500" >> /var/db/postgres/data16/postgresql.conf'

# Configure authentication (pg_hba.conf)
bastille cmd postgres sh -c 'cat >> /var/db/postgres/data16/pg_hba.conf << EOF

# API jails
host    trading_prod    app_prod    10.0.0.11/32    scram-sha-256
host    trading_dev     app_dev     10.0.0.12/32    scram-sha-256
EOF'

# Start PostgreSQL
bastille cmd postgres service postgresql start

# Create databases and users
# Generate secure passwords
PROD_PASS=$(openssl rand -base64 24)
DEV_PASS=$(openssl rand -base64 24)

echo "Production DB password: $PROD_PASS"
echo "Development DB password: $DEV_PASS"
echo "Save these passwords!"

bastille cmd postgres psql -U postgres << EOF
CREATE DATABASE trading_prod;
CREATE DATABASE trading_dev;
CREATE USER app_prod WITH PASSWORD '$PROD_PASS';
CREATE USER app_dev WITH PASSWORD '$DEV_PASS';
GRANT ALL PRIVILEGES ON DATABASE trading_prod TO app_prod;
GRANT ALL PRIVILEGES ON DATABASE trading_dev TO app_dev;
\c trading_prod
GRANT ALL ON SCHEMA public TO app_prod;
\c trading_dev
GRANT ALL ON SCHEMA public TO app_dev;
EOF

# Verify databases
bastille cmd postgres psql -U postgres -c "\l"
```

### 3.3 Configure API Jails

Run for both `api-prod` and `api-dev`:

```sh
# Install packages for both API jails
for jail in api-prod api-dev; do
    bastille pkg $jail install -y \
        python311 \
        py311-pip \
        git \
        curl
done

# Create app user and directories
for jail in api-prod api-dev; do
    bastille cmd $jail pw useradd -n app -m -s /bin/sh
    bastille cmd $jail mkdir -p /app /var/log/trading-api
    bastille cmd $jail chown -R app:app /app /var/log/trading-api
done
```

### 3.4 Configure nginx Jail

```sh
# Install nginx
bastille pkg nginx install -y nginx

# Enable nginx
bastille sysrc nginx nginx_enable="YES"

# Create SSL directory
bastille cmd nginx mkdir -p /usr/local/etc/ssl/prod /usr/local/etc/ssl/dev

# Create frontend directories
bastille cmd nginx mkdir -p /usr/local/www/prod /usr/local/www/dev
```

---

## Part 4: SSL Certificates

### 4.1 Install acme.sh on Host

```sh
# Install acme.sh
pkg install -y acme.sh

# Register account (use your email)
acme.sh --register-account -m your-email@example.com
```

### 4.2 Obtain Certificates

```sh
# Stop PF temporarily to allow ACME challenge on port 80
# Or configure PF to allow port 80 temporarily

DOMAIN="trading.yourdomain.com"

# Issue certificate (standalone mode)
acme.sh --issue -d $DOMAIN --standalone

# Copy to nginx jail
bastille cp nginx ~/.acme.sh/${DOMAIN}_ecc/${DOMAIN}.cer /usr/local/etc/ssl/prod/fullchain.pem
bastille cp nginx ~/.acme.sh/${DOMAIN}_ecc/${DOMAIN}.key /usr/local/etc/ssl/prod/privkey.pem

# For development, use the same cert or create a self-signed one
bastille cmd nginx cp /usr/local/etc/ssl/prod/fullchain.pem /usr/local/etc/ssl/dev/
bastille cmd nginx cp /usr/local/etc/ssl/prod/privkey.pem /usr/local/etc/ssl/dev/

# Set permissions
bastille cmd nginx chmod 600 /usr/local/etc/ssl/prod/privkey.pem
bastille cmd nginx chmod 600 /usr/local/etc/ssl/dev/privkey.pem
```

### 4.3 Setup Certificate Auto-Renewal

```sh
# Add to crontab
crontab -e

# Add this line:
0 3 * * * acme.sh --renew-all --post-hook "bastille cmd nginx service nginx reload"
```

---

## Part 5: Deploy Application

### 5.1 Clone Repository to API Jails

```sh
# Clone to production jail
bastille cmd api-prod su -m app -c 'git clone https://github.com/yourusername/trading-analyzer.git /app'

# Clone to development jail  
bastille cmd api-dev su -m app -c 'git clone https://github.com/yourusername/trading-analyzer.git /app'
```

### 5.2 Install Python Dependencies

**For Simple Auth (Option A):**

```sh
for jail in api-prod api-dev; do
    bastille cmd $jail pip install --break-system-packages \
        uvicorn[standard] \
        fastapi \
        sqlalchemy[asyncio] \
        asyncpg \
        python-jose[cryptography] \
        argon2-cffi \
        pydantic-settings \
        python-multipart \
        pandas
done
```

**For Clerk (Option B):**

```sh
for jail in api-prod api-dev; do
    bastille cmd $jail pip install --break-system-packages \
        uvicorn[standard] \
        fastapi \
        sqlalchemy[asyncio] \
        asyncpg \
        python-jose[cryptography] \
        httpx \
        pydantic-settings \
        python-multipart \
        pandas
done
```

### 5.3 Create Environment Files

**For Simple Auth (Option A):**

Production (`api-prod`):

```sh
# Replace with your actual values
PROD_DB_PASS="your-production-db-password"
JWT_SECRET="your-generated-secret-key"  # From Part 1A.2

bastille cmd api-prod sh -c "cat > /app/.env << EOF
# Database
DATABASE_URL=postgresql+asyncpg://app_prod:${PROD_DB_PASS}@10.0.0.10/trading_prod

# Auth
JWT_SECRET_KEY=${JWT_SECRET}

# Security
ALLOWED_ORIGINS=https://trading.yourdomain.com
EOF"

bastille cmd api-prod chown app:app /app/.env
bastille cmd api-prod chmod 600 /app/.env
```

Development (`api-dev`):

```sh
# Replace with your actual values
DEV_DB_PASS="your-development-db-password"
JWT_SECRET="your-generated-secret-key"  # Can use same key or different

bastille cmd api-dev sh -c "cat > /app/.env << EOF
# Database
DATABASE_URL=postgresql+asyncpg://app_dev:${DEV_DB_PASS}@10.0.0.10/trading_dev

# Auth
JWT_SECRET_KEY=${JWT_SECRET}

# Security
ALLOWED_ORIGINS=https://trading.yourdomain.com:8443
EOF"

bastille cmd api-dev chown app:app /app/.env
bastille cmd api-dev chmod 600 /app/.env
```

**For Clerk (Option B):**

Production (`api-prod`):

```sh
# Replace with your actual values
PROD_DB_PASS="your-production-db-password"
CLERK_DOMAIN_PROD="your-app.clerk.accounts.dev"

bastille cmd api-prod sh -c "cat > /app/.env << EOF
# Database
DATABASE_URL=postgresql+asyncpg://app_prod:${PROD_DB_PASS}@10.0.0.10/trading_prod

# Clerk
CLERK_DOMAIN=${CLERK_DOMAIN_PROD}

# Security
ALLOWED_ORIGINS=https://trading.yourdomain.com
EOF"

bastille cmd api-prod chown app:app /app/.env
bastille cmd api-prod chmod 600 /app/.env
```

Development (`api-dev`):

```sh
# Replace with your actual values
DEV_DB_PASS="your-development-db-password"
CLERK_DOMAIN_DEV="your-app-dev.clerk.accounts.dev"

bastille cmd api-dev sh -c "cat > /app/.env << EOF
# Database
DATABASE_URL=postgresql+asyncpg://app_dev:${DEV_DB_PASS}@10.0.0.10/trading_dev

# Clerk
CLERK_DOMAIN=${CLERK_DOMAIN_DEV}

# Security
ALLOWED_ORIGINS=https://trading.yourdomain.com:8443
EOF"

bastille cmd api-dev chown app:app /app/.env
bastille cmd api-dev chmod 600 /app/.env
```

### 5.4 Initialize Database Schema

```sh
# Run migrations on production
bastille cmd api-prod su -m app -c 'cd /app && python -c "
from src.api.database.schema import create_tables
create_tables()
print(\"Production database initialized\")
"'

# Run migrations on development
bastille cmd api-dev su -m app -c 'cd /app && python -c "
from src.api.database.schema import create_tables
create_tables()
print(\"Development database initialized\")
"'
```

### 5.5 Create rc.d Service Script

Create the service script on the host, then copy to jails:

```sh
cat > /tmp/trading_api << 'EOF'
#!/bin/sh

# PROVIDE: trading_api
# REQUIRE: LOGIN postgresql
# KEYWORD: shutdown

. /etc/rc.subr

name="trading_api"
rcvar="trading_api_enable"

load_rc_config $name

: ${trading_api_enable:="NO"}
: ${trading_api_user:="app"}
: ${trading_api_dir:="/app"}
: ${trading_api_host:="0.0.0.0"}
: ${trading_api_port:="8000"}
: ${trading_api_workers:="2"}

pidfile="/var/run/${name}.pid"
logfile="/var/log/trading-api/${name}.log"

start_cmd="${name}_start"
stop_cmd="${name}_stop"
status_cmd="${name}_status"

trading_api_start() {
    echo "Starting ${name}..."
    cd ${trading_api_dir}
    
    # Load environment
    if [ -f ${trading_api_dir}/.env ]; then
        set -a
        . ${trading_api_dir}/.env
        set +a
    fi
    
    /usr/sbin/daemon -p ${pidfile} -u ${trading_api_user} -o ${logfile} \
        /usr/local/bin/python3.11 -m uvicorn src.api.main:app \
        --host ${trading_api_host} \
        --port ${trading_api_port} \
        --workers ${trading_api_workers}
    
    echo "${name} started."
}

trading_api_stop() {
    if [ -f ${pidfile} ]; then
        echo "Stopping ${name}..."
        kill $(cat ${pidfile}) 2>/dev/null
        rm -f ${pidfile}
        echo "${name} stopped."
    else
        echo "${name} is not running."
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
EOF

# Copy to both API jails
for jail in api-prod api-dev; do
    bastille cp $jail /tmp/trading_api /usr/local/etc/rc.d/trading_api
    bastille cmd $jail chmod +x /usr/local/etc/rc.d/trading_api
    bastille sysrc $jail trading_api_enable="YES"
done

rm /tmp/trading_api
```

### 5.6 Start API Services

```sh
# Start production API
bastille cmd api-prod service trading_api start

# Start development API
bastille cmd api-dev service trading_api start

# Verify they're running
bastille cmd api-prod service trading_api status
bastille cmd api-dev service trading_api status

# Test endpoints directly
bastille cmd api-prod curl -s http://localhost:8000/api/health
bastille cmd api-dev curl -s http://localhost:8000/api/health
```

---

## Part 6: Configure nginx

### 6.1 Create nginx Configuration

```sh
bastille cmd nginx sh -c 'cat > /usr/local/etc/nginx/nginx.conf << '\''EOF'\''
worker_processes auto;

events {
    worker_connections 1024;
}

http {
    include mime.types;
    default_type application/octet-stream;

    # Logging
    log_format main '\''$remote_addr - $remote_user [$time_local] "$request" '\''
                    '\''$status $body_bytes_sent "$http_referer" '\''
                    '\''"$http_user_agent" "$http_x_forwarded_for"'\'';
    
    access_log /var/log/nginx/access.log main;
    error_log /var/log/nginx/error.log;

    sendfile on;
    keepalive_timeout 65;
    client_max_body_size 10M;

    # Gzip compression
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml;

    # Upstream: Production API
    upstream api_prod {
        server 10.0.0.11:8000 max_fails=3 fail_timeout=30s;
        keepalive 16;
    }

    # Upstream: Development API
    upstream api_dev {
        server 10.0.0.12:8000 max_fails=3 fail_timeout=30s;
        keepalive 16;
    }

    # Rate limiting zones
    limit_req_zone $binary_remote_addr zone=api:10m rate=20r/s;
    limit_req_zone $binary_remote_addr zone=upload:10m rate=2r/s;

    # ============================================
    # PRODUCTION: Port 443
    # ============================================
    server {
        listen 443 ssl http2;
        server_name trading.yourdomain.com;

        # TLS
        ssl_certificate /usr/local/etc/ssl/prod/fullchain.pem;
        ssl_certificate_key /usr/local/etc/ssl/prod/privkey.pem;
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384;
        ssl_prefer_server_ciphers on;
        ssl_session_cache shared:SSL:10m;
        ssl_session_timeout 1d;

        # Security headers
        add_header X-Frame-Options "DENY" always;
        add_header X-Content-Type-Options "nosniff" always;
        add_header X-XSS-Protection "1; mode=block" always;
        add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
        add_header Referrer-Policy "strict-origin-when-cross-origin" always;

        # API endpoints
        location /api/ {
            limit_req zone=api burst=50 nodelay;

            proxy_pass http://api_prod;
            proxy_http_version 1.1;
            proxy_set_header Connection "";
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;

            proxy_connect_timeout 10s;
            proxy_read_timeout 60s;
            proxy_next_upstream error timeout http_502 http_503;
        }

        # Upload endpoint (stricter limits)
        location /api/import/upload {
            limit_req zone=upload burst=5 nodelay;

            proxy_pass http://api_prod;
            proxy_http_version 1.1;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;

            proxy_read_timeout 120s;
        }

        # Static frontend
        location / {
            root /usr/local/www/prod;
            index index.html;
            try_files $uri $uri.html $uri/ /index.html;

            # Cache static assets
            location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2)$ {
                expires 1y;
                add_header Cache-Control "public, immutable";
            }
        }
    }

    # ============================================
    # DEVELOPMENT: Port 8443
    # ============================================
    server {
        listen 8443 ssl http2;
        server_name trading.yourdomain.com;

        # TLS
        ssl_certificate /usr/local/etc/ssl/dev/fullchain.pem;
        ssl_certificate_key /usr/local/etc/ssl/dev/privkey.pem;
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384;
        ssl_prefer_server_ciphers on;

        # Security headers (relaxed for dev)
        add_header X-Frame-Options "SAMEORIGIN" always;
        add_header X-Content-Type-Options "nosniff" always;

        # API endpoints
        location /api/ {
            proxy_pass http://api_dev;
            proxy_http_version 1.1;
            proxy_set_header Connection "";
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;

            proxy_connect_timeout 10s;
            proxy_read_timeout 60s;
        }

        # Upload endpoint
        location /api/import/upload {
            proxy_pass http://api_dev;
            proxy_http_version 1.1;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_read_timeout 120s;
        }

        # Static frontend
        location / {
            root /usr/local/www/dev;
            index index.html;
            try_files $uri $uri.html $uri/ /index.html;
        }
    }

    # Redirect HTTP to HTTPS (if port 80 is open)
    server {
        listen 80;
        server_name trading.yourdomain.com;
        return 301 https://$server_name$request_uri;
    }
}
EOF'

# Replace domain name
bastille cmd nginx sed -i '' 's/trading.yourdomain.com/YOUR_ACTUAL_DOMAIN/g' /usr/local/etc/nginx/nginx.conf
```

### 6.2 Test and Start nginx

```sh
# Test configuration
bastille cmd nginx nginx -t

# Start nginx
bastille cmd nginx service nginx start

# Verify
bastille cmd nginx service nginx status
```

---

## Part 7: Deploy Frontend

### 7.1 Build Frontend Locally

On your development machine:

```sh
cd trading-analyzer/frontend

# Install dependencies
npm install

# Create production environment file
cat > .env.production << EOF
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_live_your_production_key
NEXT_PUBLIC_API_URL=https://trading.yourdomain.com
EOF

# Build for production
npm run build

# The output is in the 'out' directory (static export)
```

### 7.2 Upload Frontend to Server

```sh
# From your development machine
scp -r out/* root@your-server:/tmp/frontend-prod/

# On the server, copy to nginx jail
bastille cp nginx /tmp/frontend-prod /usr/local/www/prod
rm -rf /tmp/frontend-prod
```

For development frontend:

```sh
# Create development environment file
cat > .env.development << EOF
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_your_dev_key
NEXT_PUBLIC_API_URL=https://trading.yourdomain.com:8443
EOF

# Build
npm run build

# Upload
scp -r out/* root@your-server:/tmp/frontend-dev/

# On server
bastille cp nginx /tmp/frontend-dev /usr/local/www/dev
rm -rf /tmp/frontend-dev
```

---

## Part 8: Verify Deployment

### 8.1 Check All Services

```sh
# Check jail status
bastille list

# Check PostgreSQL
bastille cmd postgres service postgresql status
bastille cmd postgres psql -U postgres -c "SELECT datname FROM pg_database;"

# Check API services
bastille cmd api-prod service trading_api status
bastille cmd api-dev service trading_api status

# Check nginx
bastille cmd nginx service nginx status

# Check API health endpoints
curl -k https://localhost/api/health        # Production
curl -k https://localhost:8443/api/health   # Development
```

### 8.2 Test from External

```sh
# From another machine
curl https://trading.yourdomain.com/api/health
curl https://trading.yourdomain.com:8443/api/health

# Open in browser
# Production: https://trading.yourdomain.com
# Development: https://trading.yourdomain.com:8443
```

### 8.3 Check Logs

```sh
# API logs
bastille cmd api-prod tail -f /var/log/trading-api/trading_api.log
bastille cmd api-dev tail -f /var/log/trading-api/trading_api.log

# nginx logs
bastille cmd nginx tail -f /var/log/nginx/access.log
bastille cmd nginx tail -f /var/log/nginx/error.log

# PostgreSQL logs
bastille cmd postgres tail -f /var/db/postgres/data16/log/postgresql-*.log
```

---

## Part 9: Maintenance Scripts

### 9.1 Deployment Script

Create `/root/deploy.sh`:

```sh
#!/bin/sh
# Deploy new version to specified environment

set -e

ENV=$1
VERSION=$2

if [ -z "$ENV" ] || [ -z "$VERSION" ]; then
    echo "Usage: deploy.sh <prod|dev> <version>"
    echo "Example: deploy.sh dev main"
    echo "Example: deploy.sh prod v1.0.0"
    exit 1
fi

case $ENV in
    prod)
        JAIL="api-prod"
        ;;
    dev)
        JAIL="api-dev"
        ;;
    *)
        echo "Invalid environment: $ENV (use 'prod' or 'dev')"
        exit 1
        ;;
esac

echo "=== Deploying $VERSION to $JAIL ==="

# Stop service
echo "Stopping service..."
bastille cmd $JAIL service trading_api stop || true

# Update code
echo "Updating code..."
bastille cmd $JAIL su -m app -c "cd /app && git fetch origin && git checkout $VERSION && git pull origin $VERSION"

# Install dependencies (in case they changed)
echo "Installing dependencies..."
bastille cmd $JAIL pip install --break-system-packages -r /app/requirements.txt

# Run migrations
echo "Running migrations..."
bastille cmd $JAIL su -m app -c "cd /app && python -c 'from src.api.database.schema import create_tables; create_tables()'"

# Start service
echo "Starting service..."
bastille cmd $JAIL service trading_api start

# Health check
sleep 3
if bastille cmd $JAIL curl -sf http://localhost:8000/api/health > /dev/null; then
    echo "=== Deployment successful ==="
else
    echo "=== DEPLOYMENT FAILED - Service unhealthy ==="
    bastille cmd $JAIL tail -20 /var/log/trading-api/trading_api.log
    exit 1
fi
```

```sh
chmod +x /root/deploy.sh
```

### 9.2 Backup Script

Create `/root/backup.sh`:

```sh
#!/bin/sh
# Backup databases and configuration

set -e

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/var/backups/trading"

mkdir -p $BACKUP_DIR

echo "=== Backup started at $(date) ==="

# ZFS snapshot
echo "Creating ZFS snapshot..."
zfs snapshot -r zroot/bastille@backup-$DATE 2>/dev/null || true

# PostgreSQL dumps
echo "Dumping databases..."
bastille cmd postgres pg_dump -U postgres trading_prod | gzip > $BACKUP_DIR/trading_prod_$DATE.sql.gz
bastille cmd postgres pg_dump -U postgres trading_dev | gzip > $BACKUP_DIR/trading_dev_$DATE.sql.gz

# Environment files
echo "Backing up configuration..."
bastille cmd api-prod cat /app/.env > $BACKUP_DIR/env_prod_$DATE
bastille cmd api-dev cat /app/.env > $BACKUP_DIR/env_dev_$DATE

# Cleanup old backups (keep 7 days)
echo "Cleaning old backups..."
find $BACKUP_DIR -name "*.sql.gz" -mtime +7 -delete
find $BACKUP_DIR -name "env_*" -mtime +7 -delete

echo "=== Backup completed ==="
ls -lh $BACKUP_DIR/*$DATE*
```

```sh
chmod +x /root/backup.sh
```

Add to crontab:

```sh
crontab -e

# Add:
0 2 * * * /root/backup.sh >> /var/log/backup.log 2>&1
```

### 9.3 Health Check Script

Create `/root/healthcheck.sh`:

```sh
#!/bin/sh
# Check health of all services

ALERT_EMAIL="admin@yourdomain.com"
FAILED=0

check_service() {
    jail=$1
    service=$2
    if ! bastille cmd $jail service $service status > /dev/null 2>&1; then
        echo "ALERT: $jail/$service is down"
        FAILED=1
    fi
}

check_http() {
    jail=$1
    url=$2
    if ! bastille cmd $jail curl -sf "$url" > /dev/null 2>&1; then
        echo "ALERT: $jail HTTP check failed: $url"
        FAILED=1
    fi
}

# Check services
check_service postgres postgresql
check_service api-prod trading_api
check_service api-dev trading_api
check_service nginx nginx

# Check HTTP endpoints
check_http api-prod "http://localhost:8000/api/health"
check_http api-dev "http://localhost:8000/api/health"

# Check disk space
DISK_USAGE=$(df -h / | awk 'NR==2 {print int($5)}')
if [ "$DISK_USAGE" -gt 80 ]; then
    echo "ALERT: Disk usage at ${DISK_USAGE}%"
    FAILED=1
fi

# Send alert if any check failed
if [ $FAILED -eq 1 ]; then
    echo "Health check failed at $(date)" | mail -s "Trading Analyzer Alert" $ALERT_EMAIL
fi

exit $FAILED
```

```sh
chmod +x /root/healthcheck.sh

# Add to crontab
crontab -e

# Add:
*/5 * * * * /root/healthcheck.sh >> /var/log/healthcheck.log 2>&1
```

---

## Part 10: Common Operations

### Start All Jails on Boot

Jails start automatically if bastille is enabled. Verify:

```sh
sysrc bastille_enable
# Should show: bastille_enable: YES
```

### Restart All Services

```sh
bastille cmd postgres service postgresql restart
bastille cmd api-prod service trading_api restart
bastille cmd api-dev service trading_api restart
bastille cmd nginx service nginx restart
```

### View Resource Usage

```sh
# Per-jail resource usage
top -J

# Jail list with IPs
bastille list -a
```

### Enter a Jail Shell

```sh
# Interactive shell in jail
bastille console api-prod

# Run single command
bastille cmd api-prod whoami
```

### Update FreeBSD in Jails

```sh
# Update base jail template
bastille update 15.0-RELEASE

# Apply updates to all jails
for jail in postgres api-prod api-dev nginx; do
    bastille update $jail
done
```

### Stop Everything

```sh
# Stop all jails
bastille stop ALL

# Or individually
bastille stop nginx
bastille stop api-prod
bastille stop api-dev
bastille stop postgres
```

---

## Troubleshooting

### API Won't Start

```sh
# Check logs
bastille cmd api-prod tail -50 /var/log/trading-api/trading_api.log

# Try starting manually
bastille cmd api-prod su -m app -c 'cd /app && python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000'
```

### Database Connection Failed

```sh
# Check PostgreSQL is running
bastille cmd postgres service postgresql status

# Test connection from API jail
bastille cmd api-prod su -m app -c 'python -c "
import asyncio
import asyncpg
asyncio.run(asyncpg.connect(\"postgresql://app_prod:PASSWORD@10.0.0.10/trading_prod\"))
print(\"Connected!\")
"'

# Check pg_hba.conf allows connection
bastille cmd postgres cat /var/db/postgres/data16/pg_hba.conf
```

### nginx Returns 502

```sh
# Check if API is running
bastille cmd api-prod curl -v http://localhost:8000/api/health

# Check nginx can reach API
bastille cmd nginx curl -v http://10.0.0.11:8000/api/health

# Check PF rules
pfctl -sr | grep 10.0.0
```

### Clerk Token Verification Fails

```sh
# Check API can reach Clerk
bastille cmd api-prod curl -v https://your-app.clerk.accounts.dev/.well-known/jwks.json

# Check CLERK_DOMAIN in .env
bastille cmd api-prod cat /app/.env | grep CLERK
```

---

## Security Checklist

- [ ] PF firewall enabled and configured
- [ ] SSH key authentication only (disable password auth)
- [ ] SSL certificates installed and auto-renewing
- [ ] Database passwords are strong and unique
- [ ] JWT secret key is strong (32+ bytes) - *Simple Auth only*
- [ ] Environment files have restrictive permissions (600)
- [ ] Rate limiting configured in nginx
- [ ] Regular backups configured and tested
- [ ] Health monitoring in place

---

## Appendix A: Simple Auth Implementation

If using Simple Auth (Option A), create these files in your application:

### A.1 Auth Configuration

Create `src/api/auth/config.py`:

```python
import os
from datetime import timedelta

# Generate with: openssl rand -base64 32
SECRET_KEY = os.environ["JWT_SECRET_KEY"]
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE = timedelta(hours=24)

# Password requirements
MIN_PASSWORD_LENGTH = 10

# Rate limiting
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_DURATION = timedelta(minutes=15)
```

### A.2 Password and Token Utilities

Create `src/api/auth/utils.py`:

```python
from datetime import datetime, timedelta
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from jose import jwt
from .config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE, MIN_PASSWORD_LENGTH

ph = PasswordHasher(
    time_cost=3,
    memory_cost=65536,  # 64MB
    parallelism=4,
)

def hash_password(password: str) -> str:
    return ph.hash(password)

def verify_password(password: str, hash: str) -> bool:
    try:
        ph.verify(hash, password)
        return True
    except VerifyMismatchError:
        return False

def validate_password(password: str) -> str | None:
    """Returns error message if invalid, None if valid."""
    if len(password) < MIN_PASSWORD_LENGTH:
        return f"Password must be at least {MIN_PASSWORD_LENGTH} characters"
    if not any(c.isupper() for c in password):
        return "Password must contain at least one uppercase letter"
    if not any(c.islower() for c in password):
        return "Password must contain at least one lowercase letter"
    if not any(c.isdigit() for c in password):
        return "Password must contain at least one number"
    return None

def create_access_token(user_id: str, email: str) -> str:
    expire = datetime.utcnow() + ACCESS_TOKEN_EXPIRE
    payload = {
        "sub": user_id,
        "email": email,
        "exp": expire,
        "iat": datetime.utcnow(),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except:
        return None
```

### A.3 Rate Limiting

Create `src/api/auth/rate_limit.py`:

```python
from collections import defaultdict
from datetime import datetime, timedelta
from .config import MAX_LOGIN_ATTEMPTS, LOCKOUT_DURATION

_attempts: dict[str, list[datetime]] = defaultdict(list)
_lockouts: dict[str, datetime] = {}

def is_locked_out(identifier: str) -> bool:
    if identifier in _lockouts:
        if datetime.utcnow() < _lockouts[identifier]:
            return True
        del _lockouts[identifier]
    return False

def record_failed_attempt(identifier: str) -> None:
    now = datetime.utcnow()
    cutoff = now - LOCKOUT_DURATION
    _attempts[identifier] = [t for t in _attempts[identifier] if t > cutoff]
    _attempts[identifier].append(now)
    if len(_attempts[identifier]) >= MAX_LOGIN_ATTEMPTS:
        _lockouts[identifier] = now + LOCKOUT_DURATION

def clear_attempts(identifier: str) -> None:
    _attempts.pop(identifier, None)
    _lockouts.pop(identifier, None)

def get_remaining_attempts(identifier: str) -> int:
    cutoff = datetime.utcnow() - LOCKOUT_DURATION
    recent = [t for t in _attempts.get(identifier, []) if t > cutoff]
    return max(0, MAX_LOGIN_ATTEMPTS - len(recent))
```

### A.4 Auth Dependency

Create `src/api/auth/dependencies.py`:

```python
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from .utils import decode_token

security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    payload = decode_token(credentials.credentials)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    user_id = payload.get("sub")
    email = payload.get("email")
    
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    return {"user_id": user_id, "email": email}
```

### A.5 Auth Router

Create `src/api/auth/router.py`:

```python
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, EmailStr
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from src.api.database.connection import get_db
from .utils import hash_password, verify_password, validate_password, create_access_token
from .rate_limit import is_locked_out, record_failed_attempt, clear_attempts, get_remaining_attempts

router = APIRouter(prefix="/auth", tags=["Authentication"])

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class UserResponse(BaseModel):
    user_id: str
    email: str

@router.post("/register", response_model=UserResponse)
async def register(
    request: RegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    error = validate_password(request.password)
    if error:
        raise HTTPException(status_code=400, detail=error)
    
    result = await db.execute(
        text("SELECT user_id FROM users WHERE email = :email"),
        {"email": request.email.lower()}
    )
    if result.fetchone():
        raise HTTPException(status_code=400, detail="Email already registered")
    
    user_id = str(uuid.uuid4())
    password_hash = hash_password(request.password)
    
    await db.execute(
        text("""
            INSERT INTO users (user_id, email, password_hash, created_at)
            VALUES (:user_id, :email, :password_hash, NOW())
        """),
        {"user_id": user_id, "email": request.email.lower(), "password_hash": password_hash}
    )
    await db.commit()
    
    return {"user_id": user_id, "email": request.email.lower()}

@router.post("/login", response_model=TokenResponse)
async def login(
    request: LoginRequest,
    req: Request,
    db: AsyncSession = Depends(get_db),
):
    email = request.email.lower()
    client_ip = req.client.host if req.client else "unknown"
    identifier = f"{email}:{client_ip}"
    
    if is_locked_out(identifier):
        raise HTTPException(status_code=429, detail="Too many failed attempts. Try again later.")
    
    result = await db.execute(
        text("SELECT user_id, email, password_hash FROM users WHERE email = :email"),
        {"email": email}
    )
    user = result.fetchone()
    
    if not user or not verify_password(request.password, user.password_hash):
        record_failed_attempt(identifier)
        remaining = get_remaining_attempts(identifier)
        raise HTTPException(status_code=401, detail=f"Invalid email or password. {remaining} attempts remaining.")
    
    clear_attempts(identifier)
    
    await db.execute(
        text("UPDATE users SET last_login = NOW() WHERE user_id = :user_id"),
        {"user_id": user.user_id}
    )
    await db.commit()
    
    token = create_access_token(user.user_id, user.email)
    return {"access_token": token}

@router.get("/me", response_model=UserResponse)
async def get_me(current_user: dict = Depends(get_current_user)):
    return current_user
```

### A.6 Register Router in Main App

Add to `src/api/main.py`:

```python
from src.api.auth.router import router as auth_router

app.include_router(auth_router, prefix="/api")
```

### A.7 Frontend Auth Helper

Create `frontend/src/lib/auth.ts`:

```typescript
const TOKEN_KEY = 'access_token';

export function getToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

export function isAuthenticated(): boolean {
  return !!getToken();
}

export async function login(email: string, password: string): Promise<void> {
  const res = await fetch('/api/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  });
  
  if (!res.ok) {
    const error = await res.json();
    throw new Error(error.detail || 'Login failed');
  }
  
  const data = await res.json();
  setToken(data.access_token);
}

export async function register(email: string, password: string): Promise<void> {
  const res = await fetch('/api/auth/register', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  });
  
  if (!res.ok) {
    const error = await res.json();
    throw new Error(error.detail || 'Registration failed');
  }
}

export function logout(): void {
  clearToken();
  window.location.href = '/login';
}
```

### A.8 Migrating to Clerk Later

When ready to migrate from Simple Auth to Clerk:

1. Export users: `SELECT user_id, email FROM users;`
2. Create Clerk application
3. Import users via Clerk API (they'll need to reset passwords)
4. Update `get_current_user` dependency to verify Clerk tokens
5. Replace `user_id` references with `clerk_user_id`
6. Update frontend to use Clerk SDK
7. Send password reset emails to all users

---

## Quick Reference

| Action | Command |
|--------|---------|
| List jails | `bastille list` |
| Start jail | `bastille start <jail>` |
| Stop jail | `bastille stop <jail>` |
| Jail shell | `bastille console <jail>` |
| Run command | `bastille cmd <jail> <command>` |
| View logs | `bastille cmd <jail> tail -f /var/log/...` |
| Deploy | `/root/deploy.sh <prod\|dev> <version>` |
| Backup | `/root/backup.sh` |
| Health check | `/root/healthcheck.sh` |

| URL | Purpose |
|-----|---------|
| https://trading.yourdomain.com | Production |
| https://trading.yourdomain.com:8443 | Development |
| https://trading.yourdomain.com/api/health | Production health |
| https://trading.yourdomain.com/api/docs | API documentation |