"""
Database operations for CashMate application.
Handles PostgreSQL connections and operations.
"""

import os
import logging
from typing import Dict, List, Optional, Any, Tuple
from contextlib import contextmanager
import psycopg2
from psycopg2.extras import RealDictCursor
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseManager:
    """
    Database manager for CashMate application using PostgreSQL.
    Supports user-specific schemas for multi-tenancy.
    """

    def __init__(self):
        # Check if DATABASE_URL is provided (for external databases like Aiven, Heroku, etc.)
        database_url = os.getenv('DATABASE_URL')

        if database_url:
            # Use DATABASE_URL directly
            self.connection_string = database_url
            logger.info("Using DATABASE_URL for database connection")

            # Parse DATABASE_URL for psycopg2 connections
            from urllib.parse import urlparse
            parsed = urlparse(database_url)
            self.host = parsed.hostname
            self.port = parsed.port or 5432
            self.database = parsed.path.lstrip('/')
            self.username = parsed.username
            self.password = parsed.password

        else:
            # Fall back to individual environment variables
            self.host = os.getenv('POSTGRES_HOST', 'localhost')
            self.port = os.getenv('POSTGRES_PORT', '5432')
            self.database = os.getenv('POSTGRES_DB', 'cashmate')
            self.username = os.getenv('POSTGRES_USER')
            self.password = os.getenv('POSTGRES_PASSWORD')

            if not all([self.username, self.password]):
                raise ValueError("Database credentials not found. Please set DATABASE_URL or individual POSTGRES_* environment variables")

            # Build connection string for SQLAlchemy
            self.connection_string = f"postgresql://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"
            logger.info(f"Using individual environment variables for database connection")

        # Create SQLAlchemy engine
        self.engine = create_engine(self.connection_string, echo=False)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

        logger.info(f"Database manager initialized for {self.host}:{self.port}/{self.database}")

    @contextmanager
    def get_connection(self):
        """
        Context manager for psycopg2 database connections.
        """
        connection = None
        try:
            connection = psycopg2.connect(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.username,
                password=self.password
            )
            yield connection
        except psycopg2.Error as e:
            logger.error(f"Database connection error: {e}")
            if connection:
                connection.rollback()
            raise
        finally:
            if connection:
                connection.close()

    @contextmanager
    def get_session(self):
        """
        Context manager for SQLAlchemy sessions.
        """
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            session.close()

    def test_connection(self) -> bool:
        """
        Test database connection.
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT 1")
            logger.info("Database connection test successful")
            return True
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            return False

    def get_or_create_akun(self, nama_akun: str, tipe_akun: str = 'kas') -> int:
        """
        Get existing account ID or create new account in cashmate.akun table.
        NOTE: This method is deprecated. Use get_or_create_user_account() with user schema instead.

        Args:
            nama_akun (str): Account name
            tipe_akun (str): Account type (default: 'kas')

        Returns:
            int: Account ID
        """
        logger.warning("get_or_create_akun() is deprecated. Use get_or_create_user_account() with user schema instead.")
        return 1  # Return dummy ID for backward compatibility

    def insert_transaksi(self, transaksi_data: Dict[str, Any]) -> int:
        """
        Insert transaction into cashmate.transaksi table.
        NOTE: This method is deprecated. Use insert_user_transaction() with user schema instead.

        Args:
            transaksi_data (dict): Transaction data containing:
                - tipe (str): 'pemasukan' or 'pengeluaran'
                - nominal (float): Amount
                - akun (str): Account name
                - kategori (str): Category
                - catatan (str): Notes/description

        Returns:
            int: Transaction ID
        """
        logger.warning("insert_transaksi() is deprecated. Use insert_user_transaction() with user schema instead.")
        return 1  # Return dummy ID for backward compatibility

    def get_monthly_summary(self, year: int, month: int) -> Dict[str, Any]:
        """
        Get monthly transaction summary by category.
        NOTE: This method is deprecated. Use get_user_monthly_summary() instead.

        Args:
            year (int): Year
            month (int): Month (1-12)

        Returns:
            dict: Summary data including total income, expenses, and category breakdown
        """
        logger.warning("get_monthly_summary() is deprecated. Use get_user_monthly_summary() with user schema instead.")
        # Return empty summary for backward compatibility
        return {
            'year': year,
            'month': month,
            'total_pemasukan': 0,
            'total_pengeluaran': 0,
            'saldo_bersih': 0,
            'total_transaksi': 0,
            'kategori_summary': [],
            'saldo_akun': []
        }

    def get_recent_transactions(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent transactions with account names.
        NOTE: This method is deprecated. Use get_user_recent_transactions() instead.

        Args:
            limit (int): Number of transactions to retrieve

        Returns:
            list: Recent transactions
        """
        logger.warning("get_recent_transactions() is deprecated. Use get_user_recent_transactions() with user schema instead.")
        return []

    def get_user_schema(self, user_id: int) -> str:
        """Get schema name for a specific user."""
        return f"user_{user_id}"

    def ensure_user_schema(self, user_id: int) -> bool:
        """Ensure user schema exists and is properly set up."""
        schema_name = self.get_user_schema(user_id)

        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    # Check if schema exists
                    cursor.execute("SELECT EXISTS(SELECT 1 FROM information_schema.schemata WHERE schema_name = %s)", (schema_name,))
                    schema_exists_result = cursor.fetchone()
                    schema_exists = schema_exists_result[0] if schema_exists_result else False

                    if not schema_exists:
                        logger.info(f"Creating schema {schema_name} for user {user_id}")
                        # Create user schema
                        cursor.execute(f"CREATE SCHEMA {schema_name}")

                        # Create tables in user schema
                        self._create_user_tables(cursor, schema_name)

                        # Create default accounts for user
                        self._create_default_accounts(cursor, schema_name)

                        conn.commit()
                        logger.info(f"Successfully created schema and tables for user {user_id}")
                        return True
                    else:
                        logger.info(f"Schema {schema_name} already exists for user {user_id}")
                        # Check if tables exist, create if missing
                        self._ensure_user_tables_exist(cursor, schema_name)
                        conn.commit()
                        return True

        except Exception as e:
            logger.error(f"Error ensuring user schema for {user_id}: {e}")
            return False

    def _create_user_tables(self, cursor, schema_name: str):
        """Create tables for user schema."""
        # Create akun table
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {schema_name}.akun (
                id SERIAL PRIMARY KEY,
                nama VARCHAR(100) NOT NULL UNIQUE,
                tipe VARCHAR(50) NOT NULL DEFAULT 'kas',
                saldo DECIMAL(15,2) NOT NULL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create transaksi table
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {schema_name}.transaksi (
                id SERIAL PRIMARY KEY,
                tipe VARCHAR(20) NOT NULL CHECK (tipe IN ('pemasukan', 'pengeluaran')),
                nominal DECIMAL(15,2) NOT NULL CHECK (nominal > 0),
                id_akun INTEGER NOT NULL REFERENCES {schema_name}.akun(id),
                kategori VARCHAR(100) NOT NULL,
                catatan TEXT,
                waktu TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create indexes
        cursor.execute(f"CREATE INDEX IF NOT EXISTS idx_{schema_name}_transaksi_waktu ON {schema_name}.transaksi(waktu)")
        cursor.execute(f"CREATE INDEX IF NOT EXISTS idx_{schema_name}_transaksi_tipe ON {schema_name}.transaksi(tipe)")
        cursor.execute(f"CREATE INDEX IF NOT EXISTS idx_{schema_name}_akun_nama ON {schema_name}.akun(nama)")

    def _create_default_accounts(self, cursor, schema_name: str):
        """Create default accounts for new user."""
        default_accounts = [
            ('cash', 'kas'),
            ('bca', 'bank'),
            ('bni', 'bank'),
            ('dana', 'e-wallet'),
            ('gopay', 'e-wallet')
        ]

        for account_name, account_type in default_accounts:
            cursor.execute(f"""
                INSERT INTO {schema_name}.akun (nama, tipe, saldo)
                VALUES (%s, %s, 0)
                ON CONFLICT (nama) DO NOTHING
            """, (account_name, account_type))

    def _ensure_user_tables_exist(self, cursor, schema_name: str):
        """Ensure all required tables exist in user schema."""
        # Check if akun table exists
        cursor.execute(f"""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_schema = %s AND table_name = 'akun'
            )
        """, (schema_name,))

        table_exists_result = cursor.fetchone()
        if not (table_exists_result and table_exists_result[0]):
            self._create_user_tables(cursor, schema_name)
            self._create_default_accounts(cursor, schema_name)

    def get_or_create_user_account(self, schema_name: str, account_name: str, account_type: str = 'kas') -> int:
        """Get existing account ID or create new account for user."""
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    # Set search path to user schema
                    cursor.execute(f"SET search_path TO {schema_name}")

                    # Check if account exists
                    cursor.execute("SELECT id FROM akun WHERE LOWER(nama) = LOWER(%s)", (account_name,))
                    result = cursor.fetchone()

                    if result:
                        logger.info(f"Found existing account: {account_name} with ID {result['id']}")
                        return result['id']

                    # Create new account
                    cursor.execute(
                        """
                        INSERT INTO akun (nama, tipe, saldo)
                        VALUES (%s, %s, 0)
                        RETURNING id
                        """,
                        (account_name, account_type)
                    )
                    new_id = cursor.fetchone()['id']
                    conn.commit()

                    logger.info(f"Created new account: {account_name} with ID {new_id}")
                    return new_id

        except Exception as e:
            logger.error(f"Error in get_or_create_user_account for {schema_name}: {e}")
            raise

    def insert_user_transaction(self, schema_name: str, transaction_data: Dict[str, Any]) -> int:
        """Insert transaction into user schema."""
        try:
            # Get or create account
            akun_id = self.get_or_create_user_account(schema_name, transaction_data['akun'])

            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    # Set search path to user schema
                    cursor.execute(f"SET search_path TO {schema_name}")

                    cursor.execute(
                        """
                        INSERT INTO transaksi
                        (tipe, nominal, id_akun, kategori, catatan, waktu)
                        VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                        RETURNING id
                        """,
                        (
                            transaction_data['tipe'],
                            transaction_data['nominal'],
                            akun_id,
                            transaction_data['kategori'],
                            transaction_data['catatan']
                        )
                    )
                    transaksi_id_result = cursor.fetchone()
                    transaksi_id = transaksi_id_result[0] if transaksi_id_result else None

                    # Update account balance
                    balance_change = transaction_data['nominal']
                    if transaction_data['tipe'] == 'pengeluaran':
                        balance_change = -balance_change

                    cursor.execute(
                        "UPDATE akun SET saldo = saldo + %s WHERE id = %s",
                        (balance_change, akun_id)
                    )

                    conn.commit()

                    logger.info(f"Inserted transaction ID {transaksi_id} for account {transaction_data['akun']}")
                    return transaksi_id

        except Exception as e:
            logger.error(f"Error inserting transaction for {schema_name}: {e}")
            raise

    def get_user_monthly_summary(self, schema_name: str, year: int, month: int) -> Dict[str, Any]:
        """Get monthly summary for specific user schema."""
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    # Set search path to user schema
                    cursor.execute(f"SET search_path TO {schema_name}")

                    # Get summary by category (excluding transfers)
                    cursor.execute("""
                        SELECT
                            t.tipe,
                            t.kategori,
                            SUM(t.nominal) as total,
                            COUNT(*) as jumlah_transaksi
                        FROM transaksi t
                        WHERE EXTRACT(YEAR FROM t.waktu) = %s
                          AND EXTRACT(MONTH FROM t.waktu) = %s
                          AND t.kategori != 'transfer'
                        GROUP BY t.tipe, t.kategori
                        ORDER BY t.tipe, total DESC
                    """, (year, month))
                    category_summary = cursor.fetchall()

                    # Get totals (excluding transfers)
                    cursor.execute("""
                        SELECT
                            SUM(CASE WHEN tipe = 'pemasukan' AND kategori != 'transfer' THEN nominal ELSE 0 END) as total_pemasukan,
                            SUM(CASE WHEN tipe = 'pengeluaran' AND kategori != 'transfer' THEN nominal ELSE 0 END) as total_pengeluaran,
                            COUNT(CASE WHEN kategori != 'transfer' THEN 1 END) as total_transaksi
                        FROM transaksi
                        WHERE EXTRACT(YEAR FROM waktu) = %s
                          AND EXTRACT(MONTH FROM waktu) = %s
                    """, (year, month))
                    totals = cursor.fetchone()

                    # Get account balances
                    cursor.execute("""
                        SELECT nama, saldo
                        FROM akun
                        WHERE saldo != 0
                        ORDER BY saldo DESC
                    """)
                    account_balances = cursor.fetchall()

                    summary = {
                        'year': year,
                        'month': month,
                        'total_pemasukan': float(totals['total_pemasukan'] or 0),
                        'total_pengeluaran': float(totals['total_pengeluaran'] or 0),
                        'saldo_bersih': float((totals['total_pemasukan'] or 0) - (totals['total_pengeluaran'] or 0)),
                        'total_transaksi': totals['total_transaksi'] or 0,
                        'kategori_summary': [dict(row) for row in category_summary],
                        'saldo_akun': [dict(row) for row in account_balances]
                    }

                    return summary

        except Exception as e:
            logger.error(f"Error getting monthly summary for schema {schema_name}: {e}")
            raise

    def get_user_recent_transactions(self, schema_name: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent transactions for specific user schema."""
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    # Set search path to user schema
                    cursor.execute(f"SET search_path TO {schema_name}")

                    cursor.execute("""
                        SELECT
                            t.id,
                            t.tipe,
                            t.nominal,
                            a.nama as akun,
                            t.kategori,
                            t.catatan,
                            t.waktu
                        FROM transaksi t
                        JOIN akun a ON t.id_akun = a.id
                        ORDER BY t.waktu DESC
                        LIMIT %s
                    """, (limit,))
                    transactions = cursor.fetchall()
                    return [dict(row) for row in transactions]

        except Exception as e:
            logger.error(f"Error getting recent transactions for schema {schema_name}: {e}")
            raise

    def get_user_accounts(self, schema_name: str) -> List[Dict[str, Any]]:
        """Get all accounts for a user."""
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    # Set search path to user schema
                    cursor.execute(f"SET search_path TO {schema_name}")

                    cursor.execute("SELECT nama, tipe, saldo FROM akun ORDER BY tipe, nama")
                    accounts = cursor.fetchall()

                    return [dict(account) for account in accounts]

        except Exception as e:
            logger.error(f"Error getting accounts for schema {schema_name}: {e}")
            return []

    def get_account_balance(self, schema_name: str, account_id: int) -> float:
        """Get current balance of an account."""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    # Set search path to user schema
                    cursor.execute(f"SET search_path TO {schema_name}")

                    cursor.execute("SELECT saldo FROM akun WHERE id = %s", (account_id,))
                    result = cursor.fetchone()
                    return float(result[0]) if result and result[0] is not None else 0.0

        except Exception as e:
            logger.error(f"Error getting account balance: {e}")
            return 0.0

    def get_account_name(self, schema_name: str, account_id: int) -> str:
        """Get account name by ID."""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    # Set search path to user schema
                    cursor.execute(f"SET search_path TO {schema_name}")

                    cursor.execute("SELECT nama FROM akun WHERE id = %s", (account_id,))
                    result = cursor.fetchone()
                    return result[0] if result else "Unknown Account"

        except Exception as e:
            logger.error(f"Error getting account name: {e}")
            return "Unknown Account"

    def update_account_balance(self, schema_name: str, account_id: int, balance_change: float):
        """Update account balance."""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    # Set search path to user schema
                    cursor.execute(f"SET search_path TO {schema_name}")

                    cursor.execute("UPDATE akun SET saldo = saldo + %s WHERE id = %s", (balance_change, account_id))
                    conn.commit()

        except Exception as e:
            logger.error(f"Error updating account balance: {e}")
            raise

    def insert_transfer_transactions(self, schema_name: str, transaction_data: Dict[str, Any],
                                   source_account_id: int, dest_account_id: int) -> int:
        """Insert transfer transactions."""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    # Set search path to user schema
                    cursor.execute(f"SET search_path TO {schema_name}")

                    transfer_amount = transaction_data['nominal']

                    # Insert source transaction (pengeluaran)
                    cursor.execute("""
                        INSERT INTO transaksi
                        (tipe, nominal, id_akun, kategori, catatan, waktu)
                        VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                        RETURNING id
                    """, (
                        'pengeluaran',
                        transfer_amount,
                        source_account_id,
                        'transfer',
                        f"Transfer ke {transaction_data['akun_tujuan']}: {transaction_data['catatan']}"
                    ))
                    source_transaction_id = cursor.fetchone()[0]

                    # Insert destination transaction (pemasukan)
                    cursor.execute("""
                        INSERT INTO transaksi
                        (tipe, nominal, id_akun, kategori, catatan, waktu)
                        VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                        RETURNING id
                    """, (
                        'pemasukan',
                        transfer_amount,
                        dest_account_id,
                        'transfer',
                        f"Transfer dari {transaction_data['akun_asal']}: {transaction_data['catatan']}"
                    ))
                    dest_transaction_id = cursor.fetchone()[0]

                    # Update account balances
                    cursor.execute("UPDATE akun SET saldo = saldo - %s WHERE id = %s", (transfer_amount, source_account_id))
                    cursor.execute("UPDATE akun SET saldo = saldo + %s WHERE id = %s", (transfer_amount, dest_account_id))

                    conn.commit()

                    return source_transaction_id

        except Exception as e:
            logger.error(f"Error inserting transfer transactions: {e}")
            raise

# Global database manager instance
db_manager = DatabaseManager()

def get_db():
    """
    Get database manager instance.
    """
    return db_manager