"""
Expense/transaction handlers for CashMate Telegram bot.
"""

import logging
from telegram import Update
from telegram.ext import ContextTypes

from ...core.database import get_db
from ...services.nlp_processor import get_parser
from ...services.expense_manager import ExpenseManager
from ...utils.formatters import format_currency

logger = logging.getLogger(__name__)

async def handle_transaction_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle non-command messages - process transactions."""
    message_text = update.message.text.strip()

    # Skip empty messages
    if not message_text:
        return

    # Check if message looks like a transaction
    if _is_transaction_like(message_text):
        # Process as transaction input (uses AI parser)
        await _process_transaction(update, message_text)
    else:
        # Not a transaction - provide helpful response
        await _handle_non_transaction_message(update, message_text)

def _is_transaction_like(message: str) -> bool:
    """Check if message looks like a transaction input."""
    message_lower = message.lower()

    # Transaction indicators
    transaction_keywords = [
        'beli', 'bayar', 'makan', 'minum', 'transport', 'gojek', 'grab',
        'bensin', 'parkir', 'tiket', 'belanja', 'gaji', 'uang', 'rupiah'
    ]

    # Amount patterns (numbers with k, rb, jt)
    amount_patterns = ['k', 'rb', 'jt', 'ribu', 'ratus', 'juta']

    # Check for transaction keywords
    has_keyword = any(keyword in message_lower for keyword in transaction_keywords)

    # Check for amount patterns
    has_amount = any(pattern in message_lower for pattern in amount_patterns)

    # Check for numbers (potential amounts)
    has_numbers = any(char.isdigit() for char in message)

    # Must have either keyword + amount OR just amount pattern
    return (has_keyword and has_numbers) or has_amount

async def _handle_non_transaction_message(update: Update, message: str):
    """Handle messages that are not transactions."""
    response = f"""
🤔 *Pesan tidak dikenali sebagai transaksi*

Pesan Anda: `{message}`

💡 *Untuk mencatat transaksi, gunakan:*
• `/input bakso 15k cash`
• Atau kirim pesan seperti: `bakso 15k`, `gaji 5jt`, `bensin 50rb`

📋 *Command tersedia:*
• `/help` - Lihat semua bantuan
• `/summary` - Ringkasan bulanan
• `/recent` - Transaksi terakhir
• `/accounts` - Saldo akun
• `/test` - Test koneksi
    """

    await update.message.reply_text(response, parse_mode='Markdown')

async def _process_transaction(update: Update, transaction_input: str):
    """Process transaction input using AI parser."""
    user = update.effective_user
    user_id = user.id

    try:
        # Get services
        parser = get_parser()
        expense_manager = ExpenseManager()

        # Show processing message
        processing_msg = await update.message.reply_text("🤖 Processing...")

        # Parse with AI
        try:
            parsed_data = parser.parse_transaction(transaction_input)
        except Exception as parse_error:
            logger.error(f"Transaction parsing failed: {parse_error}")
            error_message = f"""
❌ *Gagal Memproses Transaksi*

Input: `{transaction_input}`
Error: {str(parse_error)}

💡 *Saran:*
• Coba format sederhana: `bakso 15k cash`
• Atau tunggu sebentar jika sistem sibuk
            """

            await processing_msg.edit_text(error_message, parse_mode='Markdown')
            return

        # Process transaction using expense manager
        result = expense_manager.process_transaction(user_id, parsed_data)

        if not result['success']:
            error_message = f"""
❌ *Transaksi Gagal*

Input: `{transaction_input}`
Error: {result['error']}

💡 *Tips:*
• Pastikan format: `item jumlah akun`
• Contoh: `bakso 15k cash`
            """

            await processing_msg.edit_text(error_message, parse_mode='Markdown')
            return

        # Format success message based on transaction type
        success_message = _format_success_message(parsed_data, result['transaction_id'])

        # Edit the processing message with success
        await processing_msg.edit_text(success_message, parse_mode='Markdown')

    except ValueError as e:
        # Handle insufficient balance errors specifically
        logger.warning(f"Transaction validation error: {e}")
        error_message = f"""
❌ *Transaksi Gagal - Saldo Tidak Cukup*

Input: `{transaction_input}`
Error: {str(e)}

💡 *Solusi:*
• Cek saldo akun dengan `/accounts`
• Pastikan saldo mencukupi sebelum transaksi
• Atau gunakan akun lain yang memiliki saldo cukup
        """

        if 'processing_msg' in locals():
            await processing_msg.edit_text(error_message, parse_mode='Markdown')
        else:
            await update.message.reply_text(error_message, parse_mode='Markdown')

    except Exception as e:
        logger.error(f"Transaction processing error: {e}")
        error_message = f"""
❌ *Error Processing Transaction*

Input: `{transaction_input}`
Error: {str(e)}

💡 *Tips:*
• Pastikan format: `item jumlah akun`
• Contoh: `bakso 15k cash`
        """

        if 'processing_msg' in locals():
            await processing_msg.edit_text(error_message, parse_mode='Markdown')
        else:
            await update.message.reply_text(error_message, parse_mode='Markdown')

def _format_success_message(parsed_data: dict, transaction_id: int) -> str:
    """Format success message based on transaction type."""
    if parsed_data['tipe'] == 'transfer':
        success_message = f"""
🔄 *Transfer Berhasil!*

📊 *Detail Transfer:*
• *Dari:* {parsed_data['akun_asal']}
• *Ke:* {parsed_data['akun_tujuan']}
• *Nominal:* Rp {parsed_data['nominal']:,.0f}
• *Catatan:* {parsed_data['catatan']}

✅ ID Transaksi: {transaction_id}
        """
    else:
        tipe_emoji = "💰" if parsed_data['tipe'] == 'pemasukan' else "💸"
        success_message = f"""
{tipe_emoji} *Transaksi Berhasil Dicatat!*

📊 *Detail:*
• *Tipe:* {parsed_data['tipe'].title()}
• *Nominal:* Rp {parsed_data['nominal']:,.0f}
• *Akun:* {parsed_data['akun']}
• *Kategori:* {parsed_data['kategori']}
• *Catatan:* {parsed_data['catatan']}

✅ ID Transaksi: {transaction_id}
        """

    return success_message