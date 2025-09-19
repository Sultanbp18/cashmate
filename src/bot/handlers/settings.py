"""
Settings and utility handlers for CashMate Telegram bot.
Handles help and test commands.
"""

import logging
from telegram import Update
from telegram.ext import ContextTypes

from ...core.database import get_db
from ...services.nlp_processor import get_parser

logger = logging.getLogger(__name__)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command with simplified menu."""
    help_message = """
🏦 *CashMate - Simple Money Tracker*

🚀 *Quick Start:*
Cukup kirim pesan transaksi langsung:
• `gaji 50k cash` ✅
• `bakso 15k` ✅
• `bensin 30rb dana` ✅

📋 *Commands:*
• `/start` - Welcome & setup otomatis
• `/accounts` - Lihat akun & saldo
• `/summary` - Ringkasan bulan ini
• `/recent` - Transaksi terakhir
• `/test` - Test koneksi sistem
• `/help` - Bantuan ini

💡 *Smart Features:*
• 🤖 **AI Parser** - Otomatis detect transaksi
• 💰 **Auto Balance** - Update saldo otomatis
• 📊 **Multi-User** - Database terpisah per user
• ⚡ **Fast Response** - Setup otomatis saat pertama pakai

📱 *Contoh Penggunaan:*
```
User: /start
Bot: ✅ Setup otomatis selesai!

User: gaji 50k cash
Bot: ✅ Transaksi dicatat!

User: /accounts
Bot: 💳 Akun & saldo Anda...
```

❓ *Butuh Bantuan?*
Kirim pesan apapun yang bukan transaksi untuk panduan!
    """

    await update.message.reply_text(help_message, parse_mode='Markdown')

async def test_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /test command."""
    test_message = "🔧 *Testing System...*\n\n"

    # Test database
    try:
        db = get_db()
        db_status = db.test_connection()
        if db_status:
            test_message += "✅ Database: OK\n"
        else:
            test_message += "❌ Database: Failed\n"
    except Exception as e:
        test_message += f"❌ Database: Error - {str(e)}\n"

    # Test AI parser
    try:
        parser = get_parser()
        parser_status = parser.test_parser()
        if parser_status:
            test_message += "✅ AI Parser: OK\n"
        else:
            test_message += "❌ AI Parser: Failed\n"
    except Exception as e:
        test_message += f"❌ AI Parser: Error - {str(e)}\n"

    test_message += "\n🏦 Bot siap digunakan!"

    await update.message.reply_text(test_message, parse_mode='Markdown')