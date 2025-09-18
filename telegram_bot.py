"""
CashMate Telegram Bot - Simplified Version
Telegram interface for CashMate personal money tracker.
"""

import os
import logging
from datetime import datetime
from typing import Dict, Any, List
import asyncio
from telegram import Update, BotCommand
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from psycopg2.extras import RealDictCursor
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
    Simplified Telegram Bot interface for CashMate application.
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

    def get_user_schema(self, user_id: int) -> str:
        """Get schema name for a specific user."""
        return f"user_{user_id}"

    def ensure_user_schema(self, user_id: int) -> bool:
        """Ensure user schema exists and is properly set up."""
        schema_name = self.get_user_schema(user_id)

        try:
            with self.db.get_connection() as conn:
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

    def _setup_handlers(self):
        """Setup all command and message handlers."""

        # Core command handlers
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("accounts", self.accounts_command))
        self.application.add_handler(CommandHandler("summary", self.summary_command))
        self.application.add_handler(CommandHandler("recent", self.recent_command))
        self.application.add_handler(CommandHandler("test", self.test_command))

        # Message handler for natural language input
        self.application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_transaction_message)
        )

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command with auto-setup."""
        user = update.effective_user
        user_id = user.id

        # Auto-setup user database
        setup_success = self.ensure_user_schema(user_id)

        if setup_success:
            welcome_message = f"""
🏦 *CashMate - Simple Money Tracker*

Halo {user.first_name}! 👋

✅ *Database Anda sudah siap!*

💡 *Cara Pakai:*
Cukup kirim pesan transaksi langsung:
• `gaji 50k cash` ✅
• `bakso 15k` ✅
• `bensin 30rb dana` ✅

📋 *Commands:*
• `/accounts` - Lihat akun & saldo
• `/summary` - Ringkasan bulan
• `/recent` - Transaksi terakhir
• `/help` - Bantuan lengkap

🚀 *Mulai sekarang:*
Kirim transaksi pertamamu! 🎯
            """
        else:
            welcome_message = f"""
❌ *Setup Gagal*

Halo {user.first_name}, ada masalah dengan setup database Anda.

💡 *Coba:*
1. `/test` - Test koneksi sistem
2. Hubungi admin jika masalah berlanjut

Atau coba lagi nanti dengan `/start`
            """

        await update.message.reply_text(welcome_message, parse_mode='Markdown')

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
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
• `/test` - Test sistem
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

    async def accounts_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /accounts command - Show user accounts and balances."""
        user = update.effective_user
        user_id = user.id
        schema_name = self.get_user_schema(user_id)

        try:
            # Ensure user schema exists
            if not self.ensure_user_schema(user_id):
                await update.message.reply_text("❌ Gagal mengakses database Anda")
                return

            with self.db.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    # Set search path to user schema
                    cursor.execute(f"SET search_path TO {schema_name}")

                    # Get all accounts with balances
                    cursor.execute(f"SELECT nama, tipe, saldo FROM {schema_name}.akun ORDER BY tipe, nama")
                    accounts = cursor.fetchall()

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

    async def summary_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /summary command."""
        user = update.effective_user
        user_id = user.id
        schema_name = self.get_user_schema(user_id)

        try:
            # Ensure user schema exists
            if not self.ensure_user_schema(user_id):
                await update.message.reply_text("❌ Gagal mengakses database Anda")
                return

            # Default to current month
            year, month = get_current_month()

            # Get summary from user database
            summary = self._get_user_monthly_summary(schema_name, year, month)

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

    async def recent_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /recent command."""
        user = update.effective_user
        user_id = user.id
        schema_name = self.get_user_schema(user_id)

        try:
            # Ensure user schema exists
            if not self.ensure_user_schema(user_id):
                await update.message.reply_text("❌ Gagal mengakses database Anda")
                return

            # Get recent transactions for this user
            transactions = self._get_user_recent_transactions(schema_name, 10)

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

    async def test_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /test command."""
        test_message = "🔧 *Testing System...*\n\n"

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
        """Handle non-command messages - process transactions."""
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
• `/accounts` - Saldo akun
• `/test` - Test koneksi
        """

        await update.message.reply_text(response, parse_mode='Markdown')

    async def _process_transaction(self, update: Update, transaction_input: str):
        """Process transaction input using AI parser."""
        user = update.effective_user
        user_id = user.id
        schema_name = self.get_user_schema(user_id)

        try:
            # Ensure user schema exists
            if not self.ensure_user_schema(user_id):
                await update.message.reply_text("❌ Gagal mengakses database Anda")
                return

            # Show processing message
            processing_msg = await update.message.reply_text("🤖 Processing...")

            # Parse with AI
            try:
                parsed_data = self.parser.parse_transaction(transaction_input)
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

            # Insert to user-specific database
            transaction_id = self._insert_user_transaction(schema_name, parsed_data)

            # Format success message based on transaction type
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
            """

            if 'processing_msg' in locals():
                await processing_msg.edit_text(error_message, parse_mode='Markdown')
            else:
                await update.message.reply_text(error_message, parse_mode='Markdown')

    def _get_user_monthly_summary(self, schema_name: str, year: int, month: int) -> Dict[str, Any]:
        """Get monthly summary for specific user schema."""
        try:
            with self.db.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    # Set search path to user schema
                    cursor.execute(f"SET search_path TO {schema_name}")

                    # Get summary by category (excluding transfers)
                    cursor.execute(f"""
                        SELECT
                            t.tipe,
                            t.kategori,
                            SUM(t.nominal) as total,
                            COUNT(*) as jumlah_transaksi
                        FROM {schema_name}.transaksi t
                        WHERE EXTRACT(YEAR FROM t.waktu) = %s
                          AND EXTRACT(MONTH FROM t.waktu) = %s
                          AND t.kategori != 'transfer'
                        GROUP BY t.tipe, t.kategori
                        ORDER BY t.tipe, total DESC
                    """, (year, month))
                    category_summary = cursor.fetchall()

                    # Get totals (excluding transfers)
                    cursor.execute(f"""
                        SELECT
                            SUM(CASE WHEN tipe = 'pemasukan' AND kategori != 'transfer' THEN nominal ELSE 0 END) as total_pemasukan,
                            SUM(CASE WHEN tipe = 'pengeluaran' AND kategori != 'transfer' THEN nominal ELSE 0 END) as total_pengeluaran,
                            COUNT(CASE WHEN kategori != 'transfer' THEN 1 END) as total_transaksi
                        FROM {schema_name}.transaksi
                        WHERE EXTRACT(YEAR FROM waktu) = %s
                          AND EXTRACT(MONTH FROM waktu) = %s
                    """, (year, month))
                    totals = cursor.fetchone()

                    # Get account balances
                    cursor.execute(f"""
                        SELECT nama, saldo
                        FROM {schema_name}.akun
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

    def _get_user_recent_transactions(self, schema_name: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent transactions for specific user schema."""
        try:
            with self.db.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    # Set search path to user schema
                    cursor.execute(f"SET search_path TO {schema_name}")

                    cursor.execute(f"""
                        SELECT
                            t.id,
                            t.tipe,
                            t.nominal,
                            a.nama as akun,
                            t.kategori,
                            t.catatan,
                            t.waktu
                        FROM {schema_name}.transaksi t
                        JOIN {schema_name}.akun a ON t.id_akun = a.id
                        ORDER BY t.waktu DESC
                        LIMIT %s
                    """, (limit,))
                    transactions = cursor.fetchall()
                    return [dict(row) for row in transactions]

        except Exception as e:
            logger.error(f"Error getting recent transactions for schema {schema_name}: {e}")
            raise

    def _get_or_create_user_account(self, schema_name: str, account_name: str, account_type: str = None) -> int:
        """Get existing account ID or create new account for user."""
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    # Set search path to user schema
                    cursor.execute(f"SET search_path TO {schema_name}")

                    # Check if account exists
                    cursor.execute(f"SELECT id FROM {schema_name}.akun WHERE LOWER(nama) = LOWER(%s)", (account_name,))
                    result = cursor.fetchone()

                    if result:
                        return result[0] if isinstance(result, (tuple, list)) else result

                    # Auto-detect account type if not provided
                    if not account_type:
                        account_type = self._detect_account_type(account_name)

                    # Create new account
                    cursor.execute(f"""
                        INSERT INTO {schema_name}.akun (nama, tipe, saldo)
                        VALUES (%s, %s, 0)
                        RETURNING id
                    """, (account_name, account_type))
                    new_id_result = cursor.fetchone()
                    new_id = new_id_result[0] if new_id_result else None
                    conn.commit()

                    logger.info(f"Created new account '{account_name}' ({account_type}) for schema {schema_name}")
                    return new_id

        except Exception as e:
            logger.error(f"Error in get_or_create_user_account for {schema_name}: {e}")
            raise

    def _detect_account_type(self, account_name: str) -> str:
        """Detect account type based on account name."""
        name_lower = account_name.lower()

        # Specific bank detection
        specific_banks = [
            'bca', 'bri', 'bni', 'mandiri', 'btn', 'cimb', 'danamon', 'mega',
            'permata', 'panin', 'bukopin', 'maybank', 'btn', 'bjb', 'bsi'
        ]
        for bank in specific_banks:
            if bank in name_lower:
                return 'bank'

        # Generic bank keywords
        bank_keywords = ['bank', 'rekening', 'tabungan']
        if any(keyword in name_lower for keyword in bank_keywords):
            return 'bank'

        # E-wallet detection
        ewallet_keywords = ['dana', 'gopay', 'ovo', 'linkaja', 'shopeepay']
        if any(keyword in name_lower for keyword in ewallet_keywords):
            return 'e-wallet'

        # Cash detection
        cash_keywords = ['cash', 'tunai', 'uang']
        if any(keyword in name_lower for keyword in cash_keywords):
            return 'kas'

        # Default to kas (cash)
        return 'kas'

    def _insert_user_transaction(self, schema_name: str, transaksi_data: Dict[str, Any]) -> int:
        """Insert transaction into user schema."""
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    # Set search path to user schema
                    cursor.execute(f"SET search_path TO {schema_name}")

                    if transaksi_data['tipe'] == 'transfer':
                        # Handle transfer transaction
                        transaction_id = self._process_transfer_transaction(cursor, schema_name, transaksi_data)
                    else:
                        # Handle regular transaction
                        transaction_id = self._process_regular_transaction(cursor, schema_name, transaksi_data)

                # Explicit commit
                conn.commit()
                return transaction_id

        except Exception as e:
            logger.error(f"Error inserting transaction for {schema_name}: {e}")
            raise

    def _process_regular_transaction(self, cursor, schema_name: str, transaksi_data: Dict[str, Any]) -> int:
        """Process regular income/expense transaction."""
        # Get or create account
        akun_id = self._get_or_create_user_account(schema_name, transaksi_data['akun'])

        from decimal import Decimal
        cursor.execute(f"""
            INSERT INTO {schema_name}.transaksi
            (tipe, nominal, id_akun, kategori, catatan, waktu)
            VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
            RETURNING id
        """, (
            transaksi_data['tipe'],
            Decimal(str(transaksi_data['nominal'])),
            akun_id,
            transaksi_data['kategori'],
            transaksi_data['catatan']
        ))
        transaksi_id_result = cursor.fetchone()
        transaksi_id = transaksi_id_result[0] if transaksi_id_result else None

        # Update account balance
        balance_change = Decimal(str(transaksi_data['nominal']))
        if transaksi_data['tipe'] == 'pengeluaran':
            balance_change = -balance_change

        cursor.execute(f"UPDATE {schema_name}.akun SET saldo = saldo + %s WHERE id = %s", (balance_change, akun_id))

        return transaksi_id

    def _process_transfer_transaction(self, cursor, schema_name: str, transaksi_data: Dict[str, Any]) -> int:
        """Process transfer transaction between accounts."""
        # Get or create source and destination accounts
        source_account_id = self._get_or_create_user_account(schema_name, transaksi_data['akun_asal'])
        dest_account_id = self._get_or_create_user_account(schema_name, transaksi_data['akun_tujuan'])

        # Check source account balance
        cursor.execute(f"SELECT saldo FROM {schema_name}.akun WHERE id = %s", (source_account_id,))
        source_balance_result = cursor.fetchone()
        source_balance = source_balance_result[0] if source_balance_result else 0

        from decimal import Decimal
        transfer_amount = Decimal(str(transaksi_data['nominal']))

        if source_balance < transfer_amount:
            raise ValueError(f"Insufficient balance in {transaksi_data['akun_asal']}. Available: Rp {source_balance:,.0f}, Needed: Rp {transfer_amount:,.0f}")

        # Insert transfer transactions
        cursor.execute(f"""
            INSERT INTO {schema_name}.transaksi
            (tipe, nominal, id_akun, kategori, catatan, waktu)
            VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
            RETURNING id
        """, (
            'pengeluaran',
            transfer_amount,
            source_account_id,
            'transfer',
            f"Transfer ke {transaksi_data['akun_tujuan']}: {transaksi_data['catatan']}"
        ))
        source_transaction_id_result = cursor.fetchone()
        source_transaction_id = source_transaction_id_result[0] if source_transaction_id_result else None

        cursor.execute(f"""
            INSERT INTO {schema_name}.transaksi
            (tipe, nominal, id_akun, kategori, catatan, waktu)
            VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
            RETURNING id
        """, (
            'pemasukan',
            transfer_amount,
            dest_account_id,
            'transfer',
            f"Transfer dari {transaksi_data['akun_asal']}: {transaksi_data['catatan']}"
        ))
        dest_transaction_id_result = cursor.fetchone()
        dest_transaction_id = dest_transaction_id_result[0] if dest_transaction_id_result else None

        # Update account balances
        cursor.execute(f"UPDATE {schema_name}.akun SET saldo = saldo - %s WHERE id = %s", (transfer_amount, source_account_id))
        cursor.execute(f"UPDATE {schema_name}.akun SET saldo = saldo + %s WHERE id = %s", (transfer_amount, dest_account_id))

        return source_transaction_id

    async def setup_bot_commands(self):
        """Setup simplified bot commands menu."""
        commands = [
            BotCommand("start", "Mulai menggunakan CashMate"),
            BotCommand("help", "Bantuan dan panduan"),
            BotCommand("accounts", "Lihat akun & saldo"),
            BotCommand("summary", "Ringkasan bulanan"),
            BotCommand("recent", "Transaksi terakhir"),
            BotCommand("test", "Test koneksi sistem"),
        ]

        await self.application.bot.set_my_commands(commands)

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

            # Keep running
            stop_signal = asyncio.Event()

            def signal_handler():
                stop_signal.set()

            # Handle shutdown signals
            try:
                import signal
                signal.signal(signal.SIGINT, signal_handler)
                signal.signal(signal.SIGTERM, signal_handler)
            except (OSError, ValueError):
                pass

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