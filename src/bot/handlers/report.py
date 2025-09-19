"""
Report handlers for CashMate Telegram bot.
Handles summary, recent transactions, and accounts commands.
"""

import logging
from telegram import Update
from telegram.ext import ContextTypes
from psycopg2.extras import RealDictCursor

from ...core.database import get_db
from ...services.expense_manager import ExpenseManager
from ...services.report_generator import ReportGenerator
from ...utils.helpers import get_current_month, format_summary_display
from ...utils.formatters import format_currency

logger = logging.getLogger(__name__)

async def summary_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /summary command."""
    user = update.effective_user
    user_id = user.id

    try:
        # Get services
        expense_manager = ExpenseManager()

        # Default to current month
        year, month = get_current_month()

        # Get summary from user database
        summary = expense_manager.get_monthly_summary(user_id, year, month)

        # Format summary message
        summary_text = f"📊 *Ringkasan {year}-{month:02d}*\n\n"
        summary_text += f"💰 *Total Pemasukan:* {format_currency(summary['total_pemasukan'])}\n"
        summary_text += f"💸 *Total Pengeluaran:* {format_currency(summary['total_pengeluaran'])}\n"
        summary_text += f"📈 *Saldo Bersih:* {format_currency(summary['saldo_bersih'])}\n"
        summary_text += f"📊 *Total Transaksi:* {summary['total_transaksi']}\n\n"

        # Add category breakdown
        if summary['kategori_summary']:
            summary_text += "*📋 Per Kategori:*\n"
            current_type = None
            for item in summary['kategori_summary']:
                if item['tipe'] != current_type:
                    current_type = item['tipe']
                    emoji = "💰" if current_type == "pemasukan" else "💸"
                    summary_text += f"\n{emoji} *{current_type.upper()}:*\n"
                summary_text += f"• {item['kategori']}: {format_currency(item['total'])} ({item['jumlah_transaksi']}x)\n"

        # Add account balances
        if summary['saldo_akun']:
            summary_text += "\n💳 *Saldo Akun:*\n"
            for account in summary['saldo_akun']:
                summary_text += f"• {account['nama']}: {format_currency(account['saldo'])}\n"

        await update.message.reply_text(summary_text, parse_mode='Markdown')

    except Exception as e:
        logger.error(f"Summary error: {e}")
        await update.message.reply_text("❌ Error mengambil ringkasan")

async def recent_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /recent command."""
    user = update.effective_user
    user_id = user.id

    try:
        # Get services
        expense_manager = ExpenseManager()

        # Get recent transactions for this user
        transactions = expense_manager.get_recent_transactions(user_id, 10)

        if not transactions:
            await update.message.reply_text("📄 Belum ada transaksi")
            return

        recent_text = "📄 *10 Transaksi Terakhir:*\n\n"

        for i, trans in enumerate(transactions, 1):
            sign = "+" if trans['tipe'] == 'pemasukan' else "-"
            emoji = "💰" if trans['tipe'] == 'pemasukan' else "💸"

            recent_text += (
                f"{i:2d}. {emoji} {sign}Rp {trans['nominal']:,.0f}\n"
                f"    📅 {trans['waktu'].strftime('%d/%m/%Y %H:%M')}\n"
                f"    💳 {trans['akun']} | 📂 {trans['kategori']}\n"
                f"    📝 {trans['catatan']}\n\n"
            )

        await update.message.reply_text(recent_text, parse_mode='Markdown')

    except Exception as e:
        logger.error(f"Recent transactions error: {e}")
        await update.message.reply_text("❌ Error mengambil transaksi terakhir")

async def accounts_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /accounts command - Show user accounts and balances."""
    user = update.effective_user
    user_id = user.id

    try:
        # Get services
        expense_manager = ExpenseManager()

        # Get user accounts
        accounts = expense_manager.get_user_accounts(user_id)

        if not accounts:
            accounts_message = """
📭 *Belum Ada Akun*

Anda belum memiliki akun. Bot akan otomatis membuat akun saat Anda mencatat transaksi pertama.

*Coba catat transaksi:*
• `gaji 50k cash`
• `bakso 15k dana`
• `bensin 50rb bank`
            """
        else:
            # Calculate total balance
            total_balance = sum(account['saldo'] for account in accounts)

            accounts_message = f"💳 *Akun & Saldo Anda*\n\n"

            # Group by type
            accounts_by_type = {}
            for account in accounts:
                acc_type = account['tipe']
                if acc_type not in accounts_by_type:
                    accounts_by_type[acc_type] = []
                accounts_by_type[acc_type].append(account)

            for acc_type, acc_list in accounts_by_type.items():
                emoji = {
                    'kas': '💵',
                    'bank': '🏦',
                    'e-wallet': '📱'
                }.get(acc_type, '📋')

                accounts_message += f"{emoji} *{acc_type.upper()}:*\n"
                for account in acc_list:
                    accounts_message += f"• {account['nama']}: Rp {account['saldo']:,.0f}\n"
                accounts_message += "\n"

            # Total balance
            accounts_message += f"💰 *Total Saldo:* Rp {total_balance:,.0f}\n"

        await update.message.reply_text(accounts_message, parse_mode='Markdown')

    except Exception as e:
        logger.error(f"Accounts error for user {user_id}: {e}")
        await update.message.reply_text("❌ Error mengambil data akun")