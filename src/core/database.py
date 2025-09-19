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
    Operates exclusively within the cashmate schema.
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

        Args:
            nama_akun (str): Account name
            tipe_akun (str): Account type (default: 'kas')

        Returns:
            int: Account ID
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    # Check if account exists
                    cursor.execute(
                        "SELECT id FROM cashmate.akun WHERE LOWER(nama) = LOWER(%s)",
                        (nama_akun,)
                    )
                    result = cursor.fetchone()

                    if result:
                        logger.info(f"Found existing account: {nama_akun} with ID {result['id']}")
                        return result['id']

                    # Create new account
                    cursor.execute(
                        """
                        INSERT INTO cashmate.akun (nama, tipe, saldo)
                        VALUES (%s, %s, 0)
                        RETURNING id
                        """,
                        (nama_akun, tipe_akun)
                    )
                    new_id = cursor.fetchone()['id']
                    conn.commit()

                    logger.info(f"Created new account: {nama_akun} with ID {new_id}")
                    return new_id

        except Exception as e:
            logger.error(f"Error in get_or_create_akun: {e}")
            raise

    def insert_transaksi(self, transaksi_data: Dict[str, Any]) -> int:
        """
        Insert transaction into cashmate.transaksi table.

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
        try:
            # Get or create account
            akun_id = self.get_or_create_akun(transaksi_data['akun'])

            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO cashmate.transaksi
                        (tipe, nominal, id_akun, kategori, catatan, waktu)
                        VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                        RETURNING id
                        """,
                        (
                            transaksi_data['tipe'],
                            transaksi_data['nominal'],
                            akun_id,
                            transaksi_data['kategori'],
                            transaksi_data['catatan']
                        )
                    )
                    transaksi_id_result = cursor.fetchone()
                    transaksi_id = transaksi_id_result[0] if transaksi_id_result else None

                    # Update account balance
                    balance_change = transaksi_data['nominal']
                    if transaksi_data['tipe'] == 'pengeluaran':
                        balance_change = -balance_change

                    cursor.execute(
                        "UPDATE cashmate.akun SET saldo = saldo + %s WHERE id = %s",
                        (balance_change, akun_id)
                    )

                    conn.commit()

                    logger.info(f"Inserted transaction ID {transaksi_id} for account {transaksi_data['akun']}")
                    return transaksi_id

        except Exception as e:
            logger.error(f"Error inserting transaction: {e}")
            raise

    def get_monthly_summary(self, year: int, month: int) -> Dict[str, Any]:
        """
        Get monthly transaction summary by category.

        Args:
            year (int): Year
            month (int): Month (1-12)

        Returns:
            dict: Summary data including total income, expenses, and category breakdown
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    # Get summary by category
                    cursor.execute(
                        """
                        SELECT
                            t.tipe,
                            t.kategori,
                            SUM(t.nominal) as total,
                            COUNT(*) as jumlah_transaksi
                        FROM cashmate.transaksi t
                        WHERE EXTRACT(YEAR FROM t.waktu) = %s
                          AND EXTRACT(MONTH FROM t.waktu) = %s
                        GROUP BY t.tipe, t.kategori
                        ORDER BY t.tipe, total DESC
                        """,
                        (year, month)
                    )
                    category_summary = cursor.fetchall()

                    # Get totals
                    cursor.execute(
                        """
                        SELECT
                            SUM(CASE WHEN tipe = 'pemasukan' THEN nominal ELSE 0 END) as total_pemasukan,
                            SUM(CASE WHEN tipe = 'pengeluaran' THEN nominal ELSE 0 END) as total_pengeluaran,
                            COUNT(*) as total_transaksi
                        FROM cashmate.transaksi
                        WHERE EXTRACT(YEAR FROM waktu) = %s
                          AND EXTRACT(MONTH FROM waktu) = %s
                        """,
                        (year, month)
                    )
                    totals = cursor.fetchone()

                    # Get account balances
                    cursor.execute(
                        """
                        SELECT nama, saldo
                        FROM cashmate.akun
                        WHERE saldo != 0
                        ORDER BY saldo DESC
                        """
                    )
                    account_balances = cursor.fetchall()

                    summary = {
                        'year': year,
                        'month': month,
                        'total_pemasukan': float(totals['total_pemasukan'] or 0),
                        'total_pengeluaran': float(totals['total_pengeluaran'] or 0),
                        'saldo_bersih': float((totals['total_pemasukan'] or 0) - (totals['total_pengeluaran'] or 0)),
                        'total_transaksi': totals['total_transaksi'],
                        'kategori_summary': [dict(row) for row in category_summary],
                        'saldo_akun': [dict(row) for row in account_balances]
                    }

                    logger.info(f"Retrieved monthly summary for {year}-{month:02d}")
                    return summary

        except Exception as e:
            logger.error(f"Error getting monthly summary: {e}")
            raise

    def get_recent_transactions(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent transactions with account names.

        Args:
            limit (int): Number of transactions to retrieve

        Returns:
            list: Recent transactions
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute(
                        """
                        SELECT
                            t.id,
                            t.tipe,
                            t.nominal,
                            a.nama as akun,
                            t.kategori,
                            t.catatan,
                            t.waktu
                        FROM cashmate.transaksi t
                        JOIN cashmate.akun a ON t.id_akun = a.id
                        ORDER BY t.waktu DESC
                        LIMIT %s
                        """,
                        (limit,)
                    )
                    transactions = cursor.fetchall()
                    return [dict(row) for row in transactions]

        except Exception as e:
            logger.error(f"Error getting recent transactions: {e}")
            raise

# Global database manager instance
db_manager = DatabaseManager()

def get_db():
    """
    Get database manager instance.
    """
    return db_manager