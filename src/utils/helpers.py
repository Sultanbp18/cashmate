"""
Helper functions for CashMate application.
"""

from datetime import datetime
from typing import Dict, Any


def get_current_month() -> tuple:
    """Get current year and month."""
    now = datetime.now()
    return now.year, now.month


def clean_transaction_input(user_input: str) -> str:
    """Clean and validate transaction input."""
    cleaned = user_input.strip()
    if cleaned.startswith('/input '):
        cleaned = cleaned[7:]
    return cleaned.strip()


def format_transaction_display(trans: Dict[str, Any]) -> str:
    """Format transaction for display."""
    from .formatters import format_currency

    sign = "+" if trans['tipe'] == 'pemasukan' else "-"
    return (
        f"{sign}{format_currency(trans['nominal'])} | "
        f"{trans['akun']} | {trans['kategori']} | "
        f"{trans['catatan']}"
    )


def format_summary_display(summary: Dict[str, Any]) -> str:
    """Format monthly summary for display."""
    from .formatters import format_currency

    year, month = summary['year'], summary['month']
    text = f"\n📊 Monthly Summary {year}-{month:02d}\n"
    text += "=" * 50 + "\n"
    text += f"💰 Income:    {format_currency(summary['total_pemasukan'])}\n"
    text += f"💸 Expenses:  {format_currency(summary['total_pengeluaran'])}\n"
    text += f"📈 Net:       {format_currency(summary['saldo_bersih'])}\n"
    text += f"📊 Total Transactions: {summary['total_transaksi']}\n"

    # Category breakdown
    if summary['kategori_summary']:
        text += "\n📋 By Category:\n" + "-" * 30 + "\n"
        current_type = None
        for item in summary['kategori_summary']:
            if item['tipe'] != current_type:
                current_type = item['tipe']
                text += f"\n{current_type.upper()}:\n"
            text += f"  {item['kategori']}: {format_currency(item['total'])} ({item['jumlah_transaksi']}x)\n"

    # Account balances
    if summary['saldo_akun']:
        text += "\n💳 Account Balances:\n" + "-" * 30 + "\n"
        for account in summary['saldo_akun']:
            text += f"  {account['nama']}: {format_currency(account['saldo'])}\n"

    return text