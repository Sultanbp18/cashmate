"""
CashMate Telegram Bot
Telegram interface for CashMate personal money tracker.
"""

import os
import logging
from datetime import datetime
from typing import Dict, Any
import asyncio
from telegram import Update, BotCommand
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv

# Import our modules
from db import get_db
from ai_parser import get_parser
from utils import (
    format_currency, get_current_month, clean_transaction_input,
    validate_month, format_transaction_display
)

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class CashMateTelegramBot:
    """
    Telegram Bot interface for CashMate application.
    """
    
    def __init__(self):
        self.token = os.getenv('TELEGRAM_BOT_TOKEN')
        if not self.token:
            raise ValueError("TELEGRAM_BOT_TOKEN not found in environment variables")
        
        self.db = get_db()
        self.parser = get_parser()
        
        # Initialize bot application
        self.application = Application.builder().token(self.token).build()
        self._setup_handlers()
        
        logger.info("CashMate Telegram Bot initialized")
    
    def _setup_handlers(self):
        """Setup all command and message handlers."""
        
        # Command handlers
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("input", self.input_command))
        self.application.add_handler(CommandHandler("summary", self.summary_command))
        self.application.add_handler(CommandHandler("recent", self.recent_command))
        self.application.add_handler(CommandHandler("balance", self.balance_command))
        self.application.add_handler(CommandHandler("test", self.test_command))
        
        # Message handler for natural language input (only for transaction-like messages)
        self.application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_transaction_message)
        )
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command."""
        user = update.effective_user
        welcome_message = f"""
🏦 *CashMate - Personal Money Tracker*

Halo {user.first_name}! 👋

Saya adalah bot untuk tracking keuangan pribadi dengan AI. 
Anda bisa mencatat transaksi dengan bahasa natural Indonesia!

*🚀 Quick Start:*
• `/input bakso 15k pake cash` - Catat transaksi
• `/summary` - Ringkasan bulanan
• `/recent` - Transaksi terakhir
• `/help` - Lihat semua command

*💡 Smart Transaction Detection:*
Bot akan otomatis mendeteksi transaksi dari pesan Anda:
• `bakso 15k cash` ✅ (langsung diproses)
• `gojek 20rb ke kantor` ✅ (langsung diproses)
• `gaji 5jt ke bank` ✅ (langsung diproses)
• `halo bot` 🤔 (akan beri panduan)

*🤖 AI Parser:*
• **Hanya digunakan** untuk transaksi yang terdeteksi
• **Hemat quota** - tidak dipanggil untuk chat biasa
• **Smart categorization** berdasarkan konteks

Selamat mencatat! 📊💰
        """
        
        await update.message.reply_text(welcome_message, parse_mode='Markdown')
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command."""
        help_message = """
🏦 *CashMate Commands*

*📝 Transaction Commands:*
• `/input <transaksi>` - Catat transaksi
  Contoh: `/input bakso 15k pake cash`

*📊 Report Commands:*
• `/summary [tahun] [bulan]` - Ringkasan bulanan
  Contoh: `/summary` atau `/summary 2024 1`
• `/recent [jumlah]` - Transaksi terakhir
  Contoh: `/recent` atau `/recent 5`
• `/balance` - Saldo semua akun

*🔧 Utility Commands:*
• `/test` - Test koneksi database & AI
• `/help` - Tampilkan bantuan ini

*💡 Smart Transaction Detection:*
Bot akan mendeteksi otomatis jika pesan Anda adalah transaksi:
• `makan siang 25k` ✅ (terdeteksi sebagai transaksi)
• `bensin 50rb dana` ✅ (terdeteksi sebagai transaksi)
• `halo bot` ❌ (tidak terdeteksi, akan beri panduan)

*🤖 AI Parser Usage:*
• **Hanya dipanggil** untuk pesan yang terdeteksi sebagai transaksi
• **Hemat quota** Gemini API - tidak dipanggil untuk chat biasa
• **Otomatis categorize** berdasarkan konteks

*💰 Format Angka:*
• `15k` = 15,000
• `500rb` = 500,000
• `2jt` = 2,000,000

*💳 Akun Support:*
cash, bank, dana, gopay, ovo, kartu kredit

*📋 Kategori Auto:*
makanan, transportasi, belanja, hiburan, kesehatan, dll
        """
        
        await update.message.reply_text(help_message, parse_mode='Markdown')
    
    async def input_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /input command."""
        if not context.args:
            await update.message.reply_text(
                "❌ Format: `/input <transaksi>`\n"
                "Contoh: `/input bakso 15k pake cash`",
                parse_mode='Markdown'
            )
            return
        
        # Join all arguments as transaction input
        transaction_input = ' '.join(context.args)
        await self._process_transaction(update, transaction_input)
    
    async def summary_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /summary command."""
        try:
            # Default to current month
            year, month = get_current_month()
            
            # Parse custom year/month if provided
            if len(context.args) >= 1:
                year = int(context.args[0])
            if len(context.args) >= 2:
                month = int(context.args[1])
                if not validate_month(month):
                    await update.message.reply_text("❌ Bulan harus 1-12")
                    return
            
            # Get summary from database
            summary = self.db.get_monthly_summary(year, month)
            
            # Format summary message
            # Use shared formatting function
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
            
        except ValueError as e:
            await update.message.reply_text(f"❌ Format salah: {str(e)}")
        except Exception as e:
            logger.error(f"Summary error: {e}")
            await update.message.reply_text("❌ Error mengambil ringkasan")
    
    async def recent_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /recent command."""
        try:
            # Default limit
            limit = 10
            
            # Parse custom limit if provided
            if context.args and len(context.args) > 0:
                limit = int(context.args[0])
                if limit > 50:  # Prevent too many messages
                    limit = 50
            
            # Get recent transactions
            transactions = self.db.get_recent_transactions(limit)
            
            if not transactions:
                await update.message.reply_text("📄 Belum ada transaksi")
                return
            
            recent_text = f"📄 *{limit} Transaksi Terakhir:*\n\n"
            
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
            
        except ValueError as e:
            await update.message.reply_text(f"❌ Limit harus berupa angka")
        except Exception as e:
            logger.error(f"Recent transactions error: {e}")
            await update.message.reply_text("❌ Error mengambil transaksi terakhir")
    
    async def balance_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /balance command."""
        try:
            # Get current month summary to show account balances
            year = datetime.now().year
            month = datetime.now().month
            summary = self.db.get_monthly_summary(year, month)
            
            if not summary['saldo_akun']:
                await update.message.reply_text("💳 Belum ada saldo di akun manapun")
                return
            
            balance_text = "💳 *Saldo Semua Akun:*\n\n"
            total_balance = 0
            
            for account in summary['saldo_akun']:
                balance_text += f"• *{account['nama']}:* Rp {account['saldo']:,.0f}\n"
                total_balance += account['saldo']
            
            balance_text += f"\n💰 *Total Saldo:* Rp {total_balance:,.0f}"
            
            await update.message.reply_text(balance_text, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Balance error: {e}")
            await update.message.reply_text("❌ Error mengambil saldo")
    
    async def test_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /test command."""
        test_message = "🔧 *Testing Connections...*\n\n"
        
        # Test database
        try:
            db_status = self.db.test_connection()
            if db_status:
                test_message += "✅ Database: OK\n"
            else:
                test_message += "❌ Database: Failed\n"
        except Exception as e:
            test_message += f"❌ Database: Error - {str(e)}\n"
        
        # Test AI parser
        try:
            parser_status = self.parser.test_parser()
            if parser_status:
                test_message += "✅ AI Parser: OK\n"
            else:
                test_message += "❌ AI Parser: Failed\n"
        except Exception as e:
            test_message += f"❌ AI Parser: Error - {str(e)}\n"
        
        test_message += "\n🏦 Bot siap digunakan!"
        
        await update.message.reply_text(test_message, parse_mode='Markdown')
    
    async def handle_transaction_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle non-command messages - only process if it looks like a transaction."""
        message_text = update.message.text.strip()

        # Skip empty messages
        if not message_text:
            return

        # Check if message looks like a transaction
        if self._is_transaction_like(message_text):
            # Process as transaction input (uses AI parser)
            await self._process_transaction(update, message_text)
        else:
            # Not a transaction - provide helpful response
            await self._handle_non_transaction_message(update, message_text)

    def _is_transaction_like(self, message: str) -> bool:
        """Check if message looks like a transaction input."""
        message_lower = message.lower()

        # Transaction indicators
        transaction_keywords = [
            'beli', 'bayar', 'makan', 'minum', 'transport', 'gojek', 'grab',
            'bensin', 'parkir', 'tiket', 'belanja', 'shopping', 'gaji',
            'salary', 'uang', 'duit', 'rupiah', 'rb', 'k', 'jt'
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

    async def _handle_non_transaction_message(self, update: Update, message: str):
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
• `/balance` - Saldo akun
• `/test` - Test koneksi
        """

        await update.message.reply_text(response, parse_mode='Markdown')
    
    async def _process_transaction(self, update: Update, transaction_input: str):
        """Process transaction input using AI parser."""
        try:
            # Show processing message
            processing_msg = await update.message.reply_text("🤖 Processing...")
            
            # Parse with AI
            parsed_data = self.parser.parse_transaction(transaction_input)
            
            # Insert to database
            transaction_id = self.db.insert_transaksi(parsed_data)
            
            # Format success message
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
            
            # Edit the processing message with success
            await processing_msg.edit_text(success_message, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Transaction processing error: {e}")
            error_message = f"""
❌ *Error Processing Transaction*

Input: `{transaction_input}`
Error: {str(e)}

💡 *Tips:*
• Pastikan format: `item jumlah akun`
• Contoh: `bakso 15k cash`
• Gunakan `/help` untuk bantuan
            """
            
            if 'processing_msg' in locals():
                await processing_msg.edit_text(error_message, parse_mode='Markdown')
            else:
                await update.message.reply_text(error_message, parse_mode='Markdown')
    
    async def setup_bot_commands(self):
        """Setup bot commands menu."""
        commands = [
            BotCommand("start", "Mulai menggunakan CashMate"),
            BotCommand("help", "Bantuan dan panduan"),
            BotCommand("input", "Catat transaksi: /input bakso 15k cash"),
            BotCommand("summary", "Ringkasan bulanan"),
            BotCommand("recent", "Transaksi terakhir"),
            BotCommand("balance", "Lihat saldo semua akun"),
            BotCommand("test", "Test koneksi database & AI"),
        ]
        
        await self.application.bot.set_my_commands(commands)
        logger.info("Bot commands menu setup completed")
    
    async def run(self):
        """Run the bot."""
        try:
            # Setup bot commands
            await self.setup_bot_commands()

            # Start bot
            logger.info("Starting CashMate Telegram Bot...")
            await self.application.initialize()
            await self.application.start()
            await self.application.updater.start_polling()

            logger.info("CashMate Telegram Bot is running!")

            # Keep running with proper event loop
            stop_signal = asyncio.Event()

            def signal_handler():
                logger.info("Received shutdown signal")
                stop_signal.set()

            # Handle shutdown signals
            try:
                import signal
                signal.signal(signal.SIGINT, lambda s, f: signal_handler())
                signal.signal(signal.SIGTERM, lambda s, f: signal_handler())
            except (OSError, ValueError):
                # Signal handling not available on this platform
                pass

            # Wait for stop signal
            await stop_signal.wait()

        except Exception as e:
            logger.error(f"Bot startup error: {e}")
            raise
        finally:
            logger.info("Stopping CashMate Telegram Bot...")
            try:
                await self.application.stop()
                await self.application.shutdown()
            except Exception as e:
                logger.error(f"Error during shutdown: {e}")

def main():
    """Main entry point for Telegram Bot."""
    try:
        # Initialize and run bot
        bot = CashMateTelegramBot()
        asyncio.run(bot.run())
        
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal bot error: {e}")

if __name__ == "__main__":
    main()