"""
Report Generator for creating various financial reports and statistics.
"""

import logging
from typing import Dict, Any, List
from datetime import datetime, timedelta

from ..core.database import DatabaseManager
from ..utils.formatters import format_currency
from ..utils.helpers import get_current_month

logger = logging.getLogger(__name__)

class ReportGenerator:
    """
    Generator for various financial reports and statistics.
    """

    def __init__(self, db_manager: DatabaseManager = None):
        self.db = db_manager or DatabaseManager()

    def generate_monthly_report(self, user_id: int, year: int = None, month: int = None) -> Dict[str, Any]:
        """
        Generate comprehensive monthly financial report.

        Args:
            user_id (int): Telegram user ID
            year (int): Year (default: current)
            month (int): Month (default: current)

        Returns:
            dict: Monthly report data
        """
        try:
            if year is None or month is None:
                year, month = get_current_month()

            schema_name = self._get_user_schema(user_id)

            # Get basic summary
            summary = self.db.get_monthly_summary(year, month)

            # Enhance with additional statistics
            report = {
                'period': f"{year}-{month:02d}",
                'summary': summary,
                'top_expenses': self._get_top_expenses(schema_name, year, month),
                'category_breakdown': self._get_category_breakdown(schema_name, year, month),
                'account_activity': self._get_account_activity(schema_name, year, month),
                'spending_trends': self._get_spending_trends(schema_name, year, month),
                'generated_at': datetime.now().isoformat()
            }

            logger.info(f"Generated monthly report for user {user_id}, period {year}-{month:02d}")
            return report

        except Exception as e:
            logger.error(f"Error generating monthly report for user {user_id}: {e}")
            return self._get_empty_report(year or datetime.now().year, month or datetime.now().month)

    def generate_yearly_report(self, user_id: int, year: int = None) -> Dict[str, Any]:
        """
        Generate yearly financial report.

        Args:
            user_id (int): Telegram user ID
            year (int): Year (default: current)

        Returns:
            dict: Yearly report data
        """
        try:
            if year is None:
                year = datetime.now().year

            schema_name = self._get_user_schema(user_id)

            # Get monthly summaries for the year
            monthly_summaries = []
            for month in range(1, 13):
                try:
                    summary = self.db.get_monthly_summary(year, month)
                    monthly_summaries.append({
                        'month': month,
                        'summary': summary
                    })
                except Exception as e:
                    logger.warning(f"Could not get summary for {year}-{month:02d}: {e}")
                    monthly_summaries.append({
                        'month': month,
                        'summary': self._get_empty_monthly_summary(year, month)
                    })

            # Calculate yearly totals
            yearly_totals = self._calculate_yearly_totals(monthly_summaries)

            report = {
                'year': year,
                'monthly_summaries': monthly_summaries,
                'yearly_totals': yearly_totals,
                'top_categories_year': self._get_top_categories_year(schema_name, year),
                'generated_at': datetime.now().isoformat()
            }

            logger.info(f"Generated yearly report for user {user_id}, year {year}")
            return report

        except Exception as e:
            logger.error(f"Error generating yearly report for user {user_id}: {e}")
            return self._get_empty_yearly_report(year or datetime.now().year)

    def generate_account_report(self, user_id: int, account_name: str = None) -> Dict[str, Any]:
        """
        Generate detailed account report.

        Args:
            user_id (int): Telegram user ID
            account_name (str): Specific account name (optional)

        Returns:
            dict: Account report data
        """
        try:
            schema_name = self._get_user_schema(user_id)

            # Get account information
            accounts = self._get_user_accounts(schema_name)

            if account_name:
                # Filter for specific account
                accounts = [acc for acc in accounts if acc['nama'].lower() == account_name.lower()]
                if not accounts:
                    raise ValueError(f"Account '{account_name}' not found")

            report = {
                'accounts': accounts,
                'account_details': {},
                'generated_at': datetime.now().isoformat()
            }

            # Get detailed information for each account
            for account in accounts:
                account_name = account['nama']
                report['account_details'][account_name] = {
                    'recent_transactions': self._get_account_transactions(schema_name, account_name, limit=20),
                    'monthly_summary': self._get_account_monthly_summary(schema_name, account_name),
                    'balance_trend': self._get_account_balance_trend(schema_name, account_name)
                }

            logger.info(f"Generated account report for user {user_id}")
            return report

        except Exception as e:
            logger.error(f"Error generating account report for user {user_id}: {e}")
            return {'error': str(e), 'accounts': [], 'generated_at': datetime.now().isoformat()}

    def _get_top_expenses(self, schema_name: str, year: int, month: int, limit: int = 5) -> List[Dict[str, Any]]:
        """Get top expense transactions for the month."""
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(f"SET search_path TO {schema_name}")
                    cursor.execute("""
                        SELECT t.nominal, t.kategori, t.catatan, a.nama as akun, t.waktu
                        FROM transaksi t
                        JOIN akun a ON t.id_akun = a.id
                        WHERE EXTRACT(YEAR FROM t.waktu) = %s
                          AND EXTRACT(MONTH FROM t.waktu) = %s
                          AND t.tipe = 'pengeluaran'
                        ORDER BY t.nominal DESC
                        LIMIT %s
                    """, (year, month, limit))
                    transactions = cursor.fetchall()

            return [dict(trans) for trans in transactions]

        except Exception as e:
            logger.error(f"Error getting top expenses: {e}")
            return []

    def _get_category_breakdown(self, schema_name: str, year: int, month: int) -> List[Dict[str, Any]]:
        """Get detailed category breakdown."""
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(f"SET search_path TO {schema_name}")
                    cursor.execute("""
                        SELECT
                            t.kategori,
                            COUNT(*) as jumlah_transaksi,
                            SUM(t.nominal) as total_nominal,
                            AVG(t.nominal) as rata_rata,
                            MIN(t.nominal) as minimal,
                            MAX(t.nominal) as maksimal
                        FROM transaksi t
                        WHERE EXTRACT(YEAR FROM t.waktu) = %s
                          AND EXTRACT(MONTH FROM t.waktu) = %s
                          AND t.tipe = 'pengeluaran'
                          AND t.kategori != 'transfer'
                        GROUP BY t.kategori
                        ORDER BY total_nominal DESC
                    """, (year, month))
                    breakdown = cursor.fetchall()

            return [dict(item) for item in breakdown]

        except Exception as e:
            logger.error(f"Error getting category breakdown: {e}")
            return []

    def _get_account_activity(self, schema_name: str, year: int, month: int) -> List[Dict[str, Any]]:
        """Get account activity summary."""
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(f"SET search_path TO {schema_name}")
                    cursor.execute("""
                        SELECT
                            a.nama,
                            a.tipe,
                            COUNT(t.id) as jumlah_transaksi,
                            COALESCE(SUM(CASE WHEN t.tipe = 'pemasukan' THEN t.nominal ELSE 0 END), 0) as total_pemasukan,
                            COALESCE(SUM(CASE WHEN t.tipe = 'pengeluaran' THEN t.nominal ELSE 0 END), 0) as total_pengeluaran,
                            a.saldo
                        FROM akun a
                        LEFT JOIN transaksi t ON a.id = t.id_akun
                            AND EXTRACT(YEAR FROM t.waktu) = %s
                            AND EXTRACT(MONTH FROM t.waktu) = %s
                        GROUP BY a.id, a.nama, a.tipe, a.saldo
                        ORDER BY a.saldo DESC
                    """, (year, month))
                    activity = cursor.fetchall()

            return [dict(item) for item in activity]

        except Exception as e:
            logger.error(f"Error getting account activity: {e}")
            return []

    def _get_spending_trends(self, schema_name: str, year: int, month: int) -> Dict[str, Any]:
        """Get spending trends compared to previous periods."""
        try:
            current_month_total = self._get_month_total(schema_name, year, month, 'pengeluaran')

            # Get previous month
            prev_date = datetime(year, month, 1) - timedelta(days=1)
            prev_year, prev_month = prev_date.year, prev_date.month
            prev_month_total = self._get_month_total(schema_name, prev_year, prev_month, 'pengeluaran')

            # Calculate trend
            if prev_month_total > 0:
                trend_percentage = ((current_month_total - prev_month_total) / prev_month_total) * 100
            else:
                trend_percentage = 0

            return {
                'current_month': current_month_total,
                'previous_month': prev_month_total,
                'trend_percentage': trend_percentage,
                'trend_direction': 'up' if trend_percentage > 0 else 'down' if trend_percentage < 0 else 'stable'
            }

        except Exception as e:
            logger.error(f"Error getting spending trends: {e}")
            return {
                'current_month': 0,
                'previous_month': 0,
                'trend_percentage': 0,
                'trend_direction': 'stable'
            }

    def _get_month_total(self, schema_name: str, year: int, month: int, transaction_type: str) -> float:
        """Get total amount for a specific month and transaction type."""
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(f"SET search_path TO {schema_name}")
                    cursor.execute("""
                        SELECT COALESCE(SUM(nominal), 0)
                        FROM transaksi
                        WHERE EXTRACT(YEAR FROM waktu) = %s
                          AND EXTRACT(MONTH FROM waktu) = %s
                          AND tipe = %s
                          AND kategori != 'transfer'
                    """, (year, month, transaction_type))
                    result = cursor.fetchone()
                    return float(result[0]) if result else 0.0

        except Exception as e:
            logger.error(f"Error getting month total: {e}")
            return 0.0

    def _calculate_yearly_totals(self, monthly_summaries: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate yearly totals from monthly summaries."""
        total_pemasukan = sum(month['summary']['total_pemasukan'] for month in monthly_summaries)
        total_pengeluaran = sum(month['summary']['total_pengeluaran'] for month in monthly_summaries)
        total_transaksi = sum(month['summary']['total_transaksi'] for month in monthly_summaries)

        return {
            'total_pemasukan': total_pemasukan,
            'total_pengeluaran': total_pengeluaran,
            'saldo_bersih': total_pemasukan - total_pengeluaran,
            'total_transaksi': total_transaksi,
            'rata_rata_bulanan': {
                'pemasukan': total_pemasukan / 12,
                'pengeluaran': total_pengeluaran / 12,
                'transaksi': total_transaksi / 12
            }
        }

    def _get_top_categories_year(self, schema_name: str, year: int) -> List[Dict[str, Any]]:
        """Get top categories for the year."""
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(f"SET search_path TO {schema_name}")
                    cursor.execute("""
                        SELECT
                            t.kategori,
                            COUNT(*) as jumlah_transaksi,
                            SUM(t.nominal) as total_nominal
                        FROM transaksi t
                        WHERE EXTRACT(YEAR FROM t.waktu) = %s
                          AND t.tipe = 'pengeluaran'
                          AND t.kategori != 'transfer'
                        GROUP BY t.kategori
                        ORDER BY total_nominal DESC
                        LIMIT 10
                    """, (year,))
                    categories = cursor.fetchall()

            return [dict(cat) for cat in categories]

        except Exception as e:
            logger.error(f"Error getting top categories for year: {e}")
            return []

    def _get_user_accounts(self, schema_name: str) -> List[Dict[str, Any]]:
        """Get all user accounts."""
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(f"SET search_path TO {schema_name}")
                    cursor.execute("SELECT nama, tipe, saldo FROM akun ORDER BY tipe, nama")
                    accounts = cursor.fetchall()

            return [dict(acc) for acc in accounts]

        except Exception as e:
            logger.error(f"Error getting user accounts: {e}")
            return []

    def _get_account_transactions(self, schema_name: str, account_name: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent transactions for a specific account."""
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(f"SET search_path TO {schema_name}")
                    cursor.execute("""
                        SELECT t.tipe, t.nominal, t.kategori, t.catatan, t.waktu
                        FROM transaksi t
                        JOIN akun a ON t.id_akun = a.id
                        WHERE a.nama = %s
                        ORDER BY t.waktu DESC
                        LIMIT %s
                    """, (account_name, limit))
                    transactions = cursor.fetchall()

            return [dict(trans) for trans in transactions]

        except Exception as e:
            logger.error(f"Error getting account transactions: {e}")
            return []

    def _get_account_monthly_summary(self, schema_name: str, account_name: str) -> Dict[str, Any]:
        """Get monthly summary for a specific account."""
        year, month = get_current_month()

        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(f"SET search_path TO {schema_name}")
                    cursor.execute("""
                        SELECT
                            COUNT(*) as jumlah_transaksi,
                            COALESCE(SUM(CASE WHEN t.tipe = 'pemasukan' THEN t.nominal ELSE 0 END), 0) as total_pemasukan,
                            COALESCE(SUM(CASE WHEN t.tipe = 'pengeluaran' THEN t.nominal ELSE 0 END), 0) as total_pengeluaran
                        FROM transaksi t
                        JOIN akun a ON t.id_akun = a.id
                        WHERE a.nama = %s
                          AND EXTRACT(YEAR FROM t.waktu) = %s
                          AND EXTRACT(MONTH FROM t.waktu) = %s
                    """, (account_name, year, month))
                    summary = cursor.fetchone()

            return dict(summary) if summary else {}

        except Exception as e:
            logger.error(f"Error getting account monthly summary: {e}")
            return {}

    def _get_account_balance_trend(self, schema_name: str, account_name: str) -> List[Dict[str, Any]]:
        """Get balance trend for a specific account over the last 6 months."""
        try:
            trends = []
            current_date = datetime.now()

            for i in range(6):
                date = current_date - timedelta(days=30 * i)
                year, month = date.year, date.month

                with self.db.get_connection() as conn:
                    with conn.cursor() as cursor:
                        cursor.execute(f"SET search_path TO {schema_name}")
                        cursor.execute("""
                            SELECT COALESCE(SUM(
                                CASE WHEN t.tipe = 'pemasukan' THEN t.nominal
                                     WHEN t.tipe = 'pengeluaran' THEN -t.nominal
                                     ELSE 0 END
                            ), 0) as net_change
                            FROM transaksi t
                            JOIN akun a ON t.id_akun = a.id
                            WHERE a.nama = %s
                              AND EXTRACT(YEAR FROM t.waktu) = %s
                              AND EXTRACT(MONTH FROM t.waktu) = %s
                        """, (account_name, year, month))
                        result = cursor.fetchone()
                        net_change = float(result[0]) if result else 0.0

                        trends.append({
                            'period': f"{year}-{month:02d}",
                            'net_change': net_change
                        })

            return trends[::-1]  # Reverse to show chronological order

        except Exception as e:
            logger.error(f"Error getting account balance trend: {e}")
            return []

    def _get_user_schema(self, user_id: int) -> str:
        """Get schema name for a specific user."""
        return f"user_{user_id}"

    def _get_empty_report(self, year: int, month: int) -> Dict[str, Any]:
        """Get empty report structure."""
        return {
            'period': f"{year}-{month:02d}",
            'summary': {
                'year': year,
                'month': month,
                'total_pemasukan': 0,
                'total_pengeluaran': 0,
                'saldo_bersih': 0,
                'total_transaksi': 0,
                'kategori_summary': [],
                'saldo_akun': []
            },
            'top_expenses': [],
            'category_breakdown': [],
            'account_activity': [],
            'spending_trends': {
                'current_month': 0,
                'previous_month': 0,
                'trend_percentage': 0,
                'trend_direction': 'stable'
            },
            'generated_at': datetime.now().isoformat()
        }

    def _get_empty_yearly_report(self, year: int) -> Dict[str, Any]:
        """Get empty yearly report structure."""
        return {
            'year': year,
            'monthly_summaries': [],
            'yearly_totals': {
                'total_pemasukan': 0,
                'total_pengeluaran': 0,
                'saldo_bersih': 0,
                'total_transaksi': 0,
                'rata_rata_bulanan': {
                    'pemasukan': 0,
                    'pengeluaran': 0,
                    'transaksi': 0
                }
            },
            'top_categories_year': [],
            'generated_at': datetime.now().isoformat()
        }

    def _get_empty_monthly_summary(self, year: int, month: int) -> Dict[str, Any]:
        """Get empty monthly summary structure."""
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