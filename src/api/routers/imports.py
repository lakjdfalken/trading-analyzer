"""
Import API router.

Provides endpoints for:
- Uploading and importing CSV transaction files
- Managing accounts
- Viewing import history
- Data management (clear, export)
"""

import io
import os

# Add parent paths for imports
import sys
import tempfile
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

from api.services.database import execute_query, get_db_connection
from create_database import create_db_schema
from db_path import DATABASE_PATH
from import_data import import_transaction_data

router = APIRouter()


# Request/Response Models
class AccountCreate(BaseModel):
    """Create account request."""

    account_name: str = Field(alias="accountName")
    broker_name: str = Field(alias="brokerName")
    currency: str
    initial_balance: float = Field(default=0.0, alias="initialBalance")
    notes: Optional[str] = None

    class Config:
        populate_by_name = True


class AccountUpdate(BaseModel):
    """Update account request."""

    account_name: Optional[str] = Field(None, alias="accountName")
    broker_name: Optional[str] = Field(None, alias="brokerName")
    currency: Optional[str] = None
    initial_balance: Optional[float] = Field(None, alias="initialBalance")
    notes: Optional[str] = None

    class Config:
        populate_by_name = True


class AccountResponse(BaseModel):
    """Account response model."""

    account_id: int = Field(alias="accountId")
    account_name: str = Field(alias="accountName")
    broker_name: str = Field(alias="brokerName")
    currency: str
    initial_balance: float = Field(alias="initialBalance")
    notes: Optional[str] = None
    transaction_count: Optional[int] = Field(None, alias="transactionCount")

    class Config:
        populate_by_name = True


class ImportResult(BaseModel):
    """Import result response."""

    success: bool
    message: str
    records_imported: int = Field(alias="recordsImported")
    records_skipped: int = Field(alias="recordsSkipped")
    total_records: int = Field(alias="totalRecords")
    account_id: int = Field(alias="accountId")
    broker: str

    class Config:
        populate_by_name = True


class BrokerInfo(BaseModel):
    """Broker information."""

    key: str
    name: str
    supported_formats: List[str] = Field(alias="supportedFormats")

    class Config:
        populate_by_name = True


class DatabaseStats(BaseModel):
    """Database statistics."""

    total_transactions: int = Field(alias="totalTransactions")
    total_accounts: int = Field(alias="totalAccounts")
    brokers: List[str]
    currencies: List[str]
    date_range: Optional[Dict[str, str]] = Field(None, alias="dateRange")
    database_size_bytes: int = Field(alias="databaseSizeBytes")

    class Config:
        populate_by_name = True


# Supported brokers
SUPPORTED_BROKERS = [
    {
        "key": "trade_nation",
        "name": "Trade Nation",
        "supported_formats": ["csv"],
    },
    {
        "key": "td365",
        "name": "TD365",
        "supported_formats": ["csv"],
    },
    {
        "key": "default",
        "name": "Generic CSV",
        "supported_formats": ["csv"],
    },
]


# Account Endpoints
@router.get("/accounts")
async def get_accounts():
    """Get all trading accounts."""
    try:
        # First try with transaction count join
        query = """
            SELECT
                a.account_id,
                a.account_name,
                a.broker_name,
                a.currency,
                a.initial_balance,
                a.notes,
                COUNT(bt."Transaction Date") as transaction_count
            FROM accounts a
            LEFT JOIN broker_transactions bt ON a.account_id = bt.account_id
            GROUP BY a.account_id
            ORDER BY a.broker_name, a.account_name
        """
        try:
            results = execute_query(query)
        except Exception:
            # Fallback: broker_transactions table might not exist yet
            query = """
                SELECT
                    account_id,
                    account_name,
                    broker_name,
                    currency,
                    initial_balance,
                    notes,
                    0 as transaction_count
                FROM accounts
                ORDER BY broker_name, account_name
            """
            results = execute_query(query)

        if not results:
            return []

        return [
            {
                "account_id": row["account_id"],
                "account_name": row["account_name"],
                "broker_name": row["broker_name"],
                "currency": row["currency"],
                "initial_balance": row["initial_balance"] or 0.0,
                "notes": row["notes"],
                "transaction_count": row["transaction_count"],
            }
            for row in results
        ]
    except Exception as e:
        print(f"Error fetching accounts: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error fetching accounts: {str(e)}"
        )


@router.get("/accounts/{account_id}", response_model=AccountResponse)
async def get_account(account_id: int):
    """Get a specific account by ID."""
    query = """
        SELECT
            a.account_id,
            a.account_name,
            a.broker_name,
            a.currency,
            a.initial_balance,
            a.notes,
            COUNT(bt."Transaction Date") as transaction_count
        FROM accounts a
        LEFT JOIN broker_transactions bt ON a.account_id = bt.account_id
        WHERE a.account_id = ?
        GROUP BY a.account_id
    """
    results = execute_query(query, (account_id,))

    if not results:
        raise HTTPException(status_code=404, detail="Account not found")

    row = results[0]
    return AccountResponse(
        accountId=row["account_id"],
        accountName=row["account_name"],
        brokerName=row["broker_name"],
        currency=row["currency"],
        initialBalance=row["initial_balance"] or 0.0,
        notes=row["notes"],
        transactionCount=row["transaction_count"],
    )


@router.post("/accounts", response_model=AccountResponse)
async def create_account(account: AccountCreate):
    """Create a new trading account."""
    with get_db_connection() as conn:
        cursor = conn.cursor()

        # Check if account name already exists for this broker
        cursor.execute(
            """
            SELECT account_id FROM accounts
            WHERE account_name = ? AND broker_name = ?
        """,
            (account.account_name, account.broker_name),
        )

        if cursor.fetchone():
            raise HTTPException(
                status_code=400,
                detail=f"Account '{account.account_name}' already exists for broker '{account.broker_name}'",
            )

        # Insert new account
        cursor.execute(
            """
            INSERT INTO accounts (account_name, broker_name, currency, initial_balance, notes)
            VALUES (?, ?, ?, ?, ?)
        """,
            (
                account.account_name,
                account.broker_name,
                account.currency,
                account.initial_balance,
                account.notes,
            ),
        )

        account_id = cursor.lastrowid
        conn.commit()

    return AccountResponse(
        accountId=account_id,
        accountName=account.account_name,
        brokerName=account.broker_name,
        currency=account.currency,
        initialBalance=account.initial_balance,
        notes=account.notes,
        transactionCount=0,
    )


@router.put("/accounts/{account_id}", response_model=AccountResponse)
async def update_account(account_id: int, account: AccountUpdate):
    """Update an existing account."""
    with get_db_connection() as conn:
        cursor = conn.cursor()

        # Check if account exists
        cursor.execute("SELECT * FROM accounts WHERE account_id = ?", (account_id,))
        existing = cursor.fetchone()

        if not existing:
            raise HTTPException(status_code=404, detail="Account not found")

        # Build update query
        updates = []
        params = []

        if account.account_name is not None:
            updates.append("account_name = ?")
            params.append(account.account_name)

        if account.broker_name is not None:
            updates.append("broker_name = ?")
            params.append(account.broker_name)

        if account.currency is not None:
            updates.append("currency = ?")
            params.append(account.currency)

        if account.initial_balance is not None:
            updates.append("initial_balance = ?")
            params.append(account.initial_balance)

        if account.notes is not None:
            updates.append("notes = ?")
            params.append(account.notes)

        if updates:
            params.append(account_id)
            cursor.execute(
                f"UPDATE accounts SET {', '.join(updates)} WHERE account_id = ?",
                params,
            )
            conn.commit()

    # Return updated account
    return await get_account(account_id)


@router.delete("/accounts/{account_id}")
async def delete_account(
    account_id: int,
    delete_transactions: bool = Query(
        False, alias="deleteTransactions", description="Also delete all transactions"
    ),
):
    """Delete an account and optionally its transactions."""
    with get_db_connection() as conn:
        cursor = conn.cursor()

        # Check if account exists
        cursor.execute("SELECT * FROM accounts WHERE account_id = ?", (account_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Account not found")

        # Check for transactions
        cursor.execute(
            "SELECT COUNT(*) as count FROM broker_transactions WHERE account_id = ?",
            (account_id,),
        )
        tx_count = cursor.fetchone()[0]

        if tx_count > 0 and not delete_transactions:
            raise HTTPException(
                status_code=400,
                detail=f"Account has {tx_count} transactions. Set deleteTransactions=true to delete them.",
            )

        # Delete transactions if requested
        if delete_transactions:
            cursor.execute(
                "DELETE FROM broker_transactions WHERE account_id = ?", (account_id,)
            )

        # Delete account
        cursor.execute("DELETE FROM accounts WHERE account_id = ?", (account_id,))
        conn.commit()

    return {
        "success": True,
        "message": f"Account deleted"
        + (f" along with {tx_count} transactions" if delete_transactions else ""),
    }


# Import Endpoints
@router.get("/brokers", response_model=List[BrokerInfo])
async def get_supported_brokers():
    """Get list of supported brokers for import."""
    return [
        BrokerInfo(
            key=b["key"],
            name=b["name"],
            supportedFormats=b["supported_formats"],
        )
        for b in SUPPORTED_BROKERS
    ]


@router.post("/upload", response_model=ImportResult)
async def upload_csv(
    file: UploadFile = File(...),
    account_id: int = Form(..., alias="accountId"),
    broker: str = Form(default="default"),
):
    """
    Upload and import a CSV transaction file.

    - **file**: CSV file containing transaction data
    - **account_id**: ID of the account to import into
    - **broker**: Broker format (trade_nation, td365, default)
    """
    # Validate broker
    valid_brokers = [b["key"] for b in SUPPORTED_BROKERS]
    if broker not in valid_brokers:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid broker. Must be one of: {', '.join(valid_brokers)}",
        )

    # Validate account exists
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM accounts WHERE account_id = ?", (account_id,))
        account = cursor.fetchone()

        if not account:
            raise HTTPException(status_code=404, detail="Account not found")

    # Validate file type
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="File must be a CSV file")

    # Save uploaded file to temp location
    try:
        content = await file.read()

        # Create temp file
        with tempfile.NamedTemporaryFile(
            mode="wb", suffix=".csv", delete=False
        ) as temp_file:
            temp_file.write(content)
            temp_path = temp_file.name

        # Get count before import
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT COUNT(*) FROM broker_transactions WHERE account_id = ?",
                (account_id,),
            )
            count_before = cursor.fetchone()[0]

        # Import the data
        result_df = import_transaction_data(
            file_path=temp_path,
            broker_name=broker,
            account_id=account_id,
        )

        # Get count after import
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT COUNT(*) FROM broker_transactions WHERE account_id = ?",
                (account_id,),
            )
            count_after = cursor.fetchone()[0]

        records_imported = count_after - count_before
        total_in_file = len(result_df) if result_df is not None else 0

        # Clean up temp file
        os.unlink(temp_path)

        return ImportResult(
            success=True,
            message=f"Successfully imported {records_imported} new records",
            recordsImported=records_imported,
            recordsSkipped=max(0, total_in_file - records_imported - count_before),
            totalRecords=count_after,
            accountId=account_id,
            broker=broker,
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except KeyError as e:
        raise HTTPException(
            status_code=400, detail=f"Missing required column in CSV: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")
    finally:
        # Clean up temp file if it exists
        if "temp_path" in locals() and os.path.exists(temp_path):
            os.unlink(temp_path)


# Database Management Endpoints
@router.get("/stats", response_model=DatabaseStats)
async def get_database_stats():
    """Get database statistics."""
    stats = {
        "total_transactions": 0,
        "total_accounts": 0,
        "brokers": [],
        "currencies": [],
        "date_range": None,
        "database_size_bytes": 0,
    }

    # Get transaction count
    results = execute_query("SELECT COUNT(*) as count FROM broker_transactions")
    stats["total_transactions"] = results[0]["count"] if results else 0

    # Get account count
    results = execute_query("SELECT COUNT(*) as count FROM accounts")
    stats["total_accounts"] = results[0]["count"] if results else 0

    # Get unique brokers
    results = execute_query(
        "SELECT DISTINCT broker_name FROM broker_transactions WHERE broker_name IS NOT NULL"
    )
    stats["brokers"] = [r["broker_name"] for r in results]

    # Get unique currencies
    results = execute_query(
        "SELECT DISTINCT Currency FROM broker_transactions WHERE Currency IS NOT NULL"
    )
    stats["currencies"] = [r["Currency"] for r in results]

    # Get date range
    results = execute_query(
        """
        SELECT
            MIN("Transaction Date") as min_date,
            MAX("Transaction Date") as max_date
        FROM broker_transactions
    """
    )
    if results and results[0]["min_date"]:
        stats["date_range"] = {
            "from": results[0]["min_date"],
            "to": results[0]["max_date"],
        }

    # Get database file size
    if os.path.exists(DATABASE_PATH):
        stats["database_size_bytes"] = os.path.getsize(DATABASE_PATH)

    return DatabaseStats(
        totalTransactions=stats["total_transactions"],
        totalAccounts=stats["total_accounts"],
        brokers=stats["brokers"],
        currencies=stats["currencies"],
        dateRange=stats["date_range"],
        databaseSizeBytes=stats["database_size_bytes"],
    )


@router.post("/init-database")
async def init_database():
    """Initialize or reset the database schema."""
    try:
        create_db_schema()
        return {"success": True, "message": "Database schema initialized"}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to initialize database: {str(e)}"
        )


@router.delete("/transactions")
async def delete_transactions(
    account_id: Optional[int] = Query(None, alias="accountId"),
    broker: Optional[str] = None,
    before_date: Optional[str] = Query(None, alias="beforeDate"),
    confirm: bool = Query(False, description="Must be true to proceed with deletion"),
):
    """
    Delete transactions with optional filters.

    - **account_id**: Only delete transactions for this account
    - **broker**: Only delete transactions from this broker
    - **before_date**: Only delete transactions before this date (ISO format)
    - **confirm**: Must be true to proceed
    """
    if not confirm:
        raise HTTPException(
            status_code=400,
            detail="Set confirm=true to proceed with deletion",
        )

    conditions = []
    params = []

    if account_id is not None:
        conditions.append("account_id = ?")
        params.append(account_id)

    if broker is not None:
        conditions.append("broker_name = ?")
        params.append(broker)

    if before_date is not None:
        conditions.append('"Transaction Date" < ?')
        params.append(before_date)

    where_clause = " AND ".join(conditions) if conditions else "1=1"

    with get_db_connection() as conn:
        cursor = conn.cursor()

        # Get count first
        cursor.execute(
            f"SELECT COUNT(*) FROM broker_transactions WHERE {where_clause}", params
        )
        count = cursor.fetchone()[0]

        if count == 0:
            return {"success": True, "message": "No transactions matched the criteria"}

        # Delete
        cursor.execute(f"DELETE FROM broker_transactions WHERE {where_clause}", params)
        conn.commit()

    return {
        "success": True,
        "message": f"Deleted {count} transactions",
        "deletedCount": count,
    }


@router.get("/export")
async def export_transactions(
    account_id: Optional[int] = Query(None, alias="accountId"),
    broker: Optional[str] = None,
    start_date: Optional[str] = Query(None, alias="startDate"),
    end_date: Optional[str] = Query(None, alias="endDate"),
    format: str = Query(default="csv", description="Export format (csv)"),
):
    """
    Export transactions to CSV.

    - **account_id**: Filter by account ID
    - **broker**: Filter by broker
    - **start_date**: Start date (ISO format)
    - **end_date**: End date (ISO format)
    - **format**: Export format (currently only csv)
    """
    conditions = []
    params = []

    if account_id is not None:
        conditions.append("account_id = ?")
        params.append(account_id)

    if broker is not None:
        conditions.append("broker_name = ?")
        params.append(broker)

    if start_date is not None:
        conditions.append('"Transaction Date" >= ?')
        params.append(start_date)

    if end_date is not None:
        conditions.append('"Transaction Date" <= ?')
        params.append(end_date)

    where_clause = " AND ".join(conditions) if conditions else "1=1"

    query = f"""
        SELECT
            "Transaction Date",
            "Ref. No.",
            "Action",
            "Description",
            "Amount",
            "Open Period",
            "Opening",
            "Closing",
            "P/L",
            "Status",
            "Balance",
            "Currency",
            broker_name,
            account_id
        FROM broker_transactions
        WHERE {where_clause}
        ORDER BY "Transaction Date" DESC
    """

    results = execute_query(query, tuple(params) if params else None)

    if not results:
        raise HTTPException(status_code=404, detail="No transactions found")

    # Convert to CSV
    import csv

    output = io.StringIO()
    if results:
        writer = csv.DictWriter(output, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)

    output.seek(0)

    # Generate filename
    filename = f"transactions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
