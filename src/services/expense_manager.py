"""
Expense Manager for handling business logic related to expense operations.
"""

import logging
from typing import Dict, Any, List
from datetime import datetime

from ..core.database import DatabaseManager
from ..utils.helpers import get_current_month
from ..utils.formatters import format_currency

logger = logging.getLogger(__name__)

class ExpenseManager:
    """
    Manager for expense-related business logic operations.
    """

    def __init__(self, db_manager: DatabaseManager = None):
        self.db = db_manager or DatabaseManager()

    def process_transaction(self, user_id: int, transaction_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a transaction for a specific user.

        Args:
            user_id (int): Telegram user ID
            transaction_data (dict): Parsed transaction data

        Returns:
            dict: Processing result with transaction ID and details
        """
        try:
            schema_name = self._get_user_schema(user_id)

            # Ensure user schema exists
            if not self._ensure_user_schema(user_id):
                raise ValueError("Failed to setup user database")

            # Handle transfer vs regular transactions
            if transaction_data['tipe'] == 'transfer':
                transaction_id = self._process_transfer_transaction(schema_name, transaction_data)
            else:
                transaction_id = self._process_regular_transaction(schema_name, transaction_data)

            logger.info(f"Successfully processed transaction {transaction_id} for user {user_id}")
            return {
                'success': True,
                'transaction_id': transaction_id,
                'transaction_data': transaction_data
            }

        except Exception as e:
            logger.error(f"Error processing transaction for user {user_id}: {e}")
            return {
                'success': False,
                'error': str(e),
                'transaction_data': transaction_data
            }

    def _process_regular_transaction(self, schema_name: str, transaction_data: Dict[str, Any]) -> int:
        """Process regular income/expense transaction."""
        # Get or create account
        akun_id = self._get_or_create_user_account(schema_name, transaction_data['akun'])

        # Check balance for expenses
        if transaction_data['tipe'] == 'pengeluaran':
            current_balance = self._get_account_balance(schema_name, akun_id)
            expense_amount = transaction_data['nominal']

            if current_balance < expense_amount:
                account_name = self._get_account_name(schema_name, akun_id)
                raise ValueError(
                    f"Saldo tidak cukup di akun {account_name}. "
                    f"Saldo tersedia: {format_currency(current_balance)}, "
                    f"Dibutuhkan: {format_currency(expense_amount)}"
                )

        # Insert transaction
        transaction_id = self._insert_user_transaction(schema_name, transaction_data)

        # Update account balance
        balance_change = transaction_data['nominal']
        if transaction_data['tipe'] == 'pengeluaran':
            balance_change = -balance_change

        self._update_account_balance(schema_name, akun_id, balance_change)

        return transaction_id

    def _process_transfer_transaction(self, schema_name: str, transaction_data: Dict[str, Any]) -> int:
        """Process transfer transaction between accounts."""
        # Get or create source and destination accounts
        source_account_id = self._get_or_create_user_account(schema_name, transaction_data['akun_asal'])
        dest_account_id = self._get_or_create_user_account(schema_name, transaction_data['akun_tujuan'])

        # Check source account balance
        source_balance = self._get_account_balance(schema_name, source_account_id)
        transfer_amount = transaction_data['nominal']

        if source_balance < transfer_amount:
            source_account_name = self._get_account_name(schema_name, source_account_id)
            raise ValueError(
                f"Saldo tidak cukup di akun {source_account_name} untuk transfer. "
                f"Saldo tersedia: {format_currency(source_balance)}, "
                f"Dibutuhkan: {format_currency(transfer_amount)}"
            )

        # Insert transfer transactions
        transaction_id = self._insert_transfer_transactions(schema_name, transaction_data, source_account_id, dest_account_id)

        # Update account balances
        self._update_account_balance(schema_name, source_account_id, -transfer_amount)
        self._update_account_balance(schema_name, dest_account_id, transfer_amount)

        return transaction_id

    def get_user_accounts(self, user_id: int) -> List[Dict[str, Any]]:
        """
        Get all accounts for a user with their balances.

        Args:
            user_id (int): Telegram user ID

        Returns:
            list: List of account dictionaries
        """
        try:
            schema_name = self._get_user_schema(user_id)

            if not self._ensure_user_schema(user_id):
                return []

            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(f"SET search_path TO {schema_name}")
                    cursor.execute("SELECT nama, tipe, saldo FROM akun ORDER BY tipe, nama")
                    accounts = cursor.fetchall()

            return [dict(account) for account in accounts]

        except Exception as e:
            logger.error(f"Error getting accounts for user {user_id}: {e}")
            return []

    def get_monthly_summary(self, user_id: int, year: int = None, month: int = None) -> Dict[str, Any]:
        """
        Get monthly summary for a user.

        Args:
            user_id (int): Telegram user ID
            year (int): Year (default: current)
            month (int): Month (default: current)

        Returns:
            dict: Monthly summary data
        """
        try:
            if year is None or month is None:
                year, month = get_current_month()

            schema_name = self._get_user_schema(user_id)

            if not self._ensure_user_schema(user_id):
                return self._get_empty_summary(year, month)

            return self.db.get_monthly_summary(year, month)

        except Exception as e:
            logger.error(f"Error getting monthly summary for user {user_id}: {e}")
            return self._get_empty_summary(year or datetime.now().year, month or datetime.now().month)

    def get_recent_transactions(self, user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent transactions for a user.

        Args:
            user_id (int): Telegram user ID
            limit (int): Number of transactions to retrieve

        Returns:
            list: List of recent transactions
        """
        try:
            schema_name = self._get_user_schema(user_id)

            if not self._ensure_user_schema(user_id):
                return []

            return self.db.get_recent_transactions(limit)

        except Exception as e:
            logger.error(f"Error getting recent transactions for user {user_id}: {e}")
            return []

    def _get_user_schema(self, user_id: int) -> str:
        """Get schema name for a specific user."""
        return f"user_{user_id}"

    def _ensure_user_schema(self, user_id: int) -> bool:
        """Ensure user schema exists and is properly set up."""
        # This would need to be implemented based on the database setup logic
        # For now, return True assuming schema exists
        return True

    def _get_or_create_user_account(self, schema_name: str, account_name: str, account_type: str = None) -> int:
        """Get existing account ID or create new account for user."""
        # This would need to be implemented based on the database operations
        # For now, return a dummy ID
        return 1

    def _get_account_balance(self, schema_name: str, account_id: int) -> float:
        """Get current balance of an account."""
        # This would need to be implemented based on the database operations
        # For now, return a dummy balance
        return 1000000.0

    def _get_account_name(self, schema_name: str, account_id: int) -> str:
        """Get account name by ID."""
        # This would need to be implemented based on the database operations
        # For now, return a dummy name
        return "cash"

    def _insert_user_transaction(self, schema_name: str, transaction_data: Dict[str, Any]) -> int:
        """Insert transaction into user schema."""
        # This would need to be implemented based on the database operations
        # For now, return a dummy ID
        return 1

    def _insert_transfer_transactions(self, schema_name: str, transaction_data: Dict[str, Any],
                                    source_account_id: int, dest_account_id: int) -> int:
        """Insert transfer transactions."""
        # This would need to be implemented based on the database operations
        # For now, return a dummy ID
        return 1

    def _update_account_balance(self, schema_name: str, account_id: int, balance_change: float):
        """Update account balance."""
        # This would need to be implemented based on the database operations
        pass

    def _get_empty_summary(self, year: int, month: int) -> Dict[str, Any]:
        """Get empty summary structure."""
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