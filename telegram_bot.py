"""
CashMate Telegram Bot
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
                    schema_exists = cursor.fetchone()[0]

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
            logger.error(f"Full error details: {str(e)}")
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
        cursor.execute(f"CREATE INDEX IF NOT EXISTS idx_{schema_name}_transaksi_kategori ON {schema_name}.transaksi(kategori)")
        cursor.execute(f"CREATE INDEX IF NOT EXISTS idx_{schema_name}_transaksi_akun ON {schema_name}.transaksi(id_akun)")
        cursor.execute(f"CREATE INDEX IF NOT EXISTS idx_{schema_name}_akun_nama ON {schema_name}.akun(nama)")

        # Create trigger for updated_at
        cursor.execute(f"""
            CREATE OR REPLACE FUNCTION {schema_name}.update_updated_at_column()
            RETURNS TRIGGER AS $$
            BEGIN
                NEW.updated_at = CURRENT_TIMESTAMP;
                RETURN NEW;
            END;
            $$ language 'plpgsql'
        """)

        cursor.execute(f"""
            DROP TRIGGER IF EXISTS update_{schema_name}_akun_updated_at ON {schema_name}.akun;
            CREATE TRIGGER update_{schema_name}_akun_updated_at
                BEFORE UPDATE ON {schema_name}.akun
                FOR EACH ROW
                EXECUTE FUNCTION {schema_name}.update_updated_at_column()
        """)

    def _create_default_accounts(self, cursor, schema_name: str):
        """Create default accounts for new user."""
        default_accounts = [
            ('cash', 'kas'),
            ('bni', 'bank'),
            ('bri', 'bank'),
            ('bca', 'bank'),
            ('dana', 'e-wallet'),
            ('gopay', 'e-wallet'),
            ('ovo', 'e-wallet')
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

        if not cursor.fetchone()[0]:
            self._create_user_tables(cursor, schema_name)
            self._create_default_accounts(cursor, schema_name)
    
    def _setup_handlers(self):
        """Setup all command and message handlers."""

        # Core command handlers (simplified)
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("accounts", self.accounts_command))
        self.application.add_handler(CommandHandler("summary", self.summary_command))
        self.application.add_handler(CommandHandler("recent", self.recent_command))
        self.application.add_handler(CommandHandler("input", self.input_command))
        self.application.add_handler(CommandHandler("test", self.test_command))
        
        # Message handler for natural language input (only for transaction-like messages)
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

*💡 Cara Pakai:*
Cukup kirim pesan transaksi langsung:
• `gaji 50k cash` ✅
• `bakso 15k` ✅
• `bensin 30rb dana` ✅

*📋 Commands:*
• `/accounts` - Lihat akun & saldo
• `/summary` - Ringkasan bulan
• `/recent` - Transaksi terakhir
• `/help` - Bantuan lengkap

*💳 Kelola Akun:*
• `mandiri bank` - Tambah akun
• `hapus mandiri` - Hapus akun

*🚀 Mulai sekarang:*
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

*🚀 Quick Start:*
Cukup kirim pesan transaksi langsung:
• `gaji 50k cash` ✅
• `bakso 15k` ✅
• `bensin 30rb dana` ✅

*📋 Commands:*
• `/start` - Welcome & setup otomatis
• `/accounts` - Lihat akun & saldo
• `/summary` - Ringkasan bulan ini
• `/recent` - Transaksi terakhir
• `/input` - Catat transaksi manual
• `/test` - Test sistem
• `/help` - Bantuan ini

*💳 Kelola Akun:*
Kirim pesan langsung (tanpa /):
• `mandiri bank` - Tambah akun bank
• `gopay e-wallet` - Tambah akun e-wallet
• `hapus mandiri` - Hapus akun

*💡 Smart Features:*
• 🤖 **AI Parser** - Otomatis detect transaksi
• 💰 **Auto Balance** - Update saldo otomatis
• 📊 **Multi-User** - Database terpisah per user
• ⚡ **Fast Response** - Setup otomatis saat pertama pakai

*📱 Contoh Penggunaan:*
```
User: /start
Bot: ✅ Setup otomatis selesai!

User: gaji 50k cash
Bot: ✅ Transaksi dicatat!

User: mandiri bank
Bot: ✅ Akun bank ditambahkan!

User: /accounts
Bot: 💳 Akun & saldo Anda...
```

*❓ Butuh Bantuan?*
Kirim pesan apapun yang bukan transaksi untuk panduan!
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

            # Parse custom year/month if provided
            if len(context.args) >= 1:
                year = int(context.args[0])
            if len(context.args) >= 2:
                month = int(context.args[1])
                if not validate_month(month):
                    await update.message.reply_text("❌ Bulan harus 1-12")
                    return

            # Get summary from user database
            logger.info(f"Getting summary for user {user_id}, schema {schema_name}, year {year}, month {month}")
            summary = self._get_user_monthly_summary(schema_name, year, month)
            logger.info(f"Summary result: {summary}")

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
        user = update.effective_user
        user_id = user.id
        schema_name = self.get_user_schema(user_id)

        try:
            # Ensure user schema exists
            if not self.ensure_user_schema(user_id):
                await update.message.reply_text("❌ Gagal mengakses database Anda")
                return

            # Default limit
            limit = 10

            # Parse custom limit if provided
            if context.args and len(context.args) > 0:
                limit = int(context.args[0])
                if limit > 50:  # Prevent too many messages
                    limit = 50

            # Get recent transactions for this user
            transactions = self._get_user_recent_transactions(schema_name, limit)
            
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

            logger.info(f"Getting accounts for user {user_id}, schema {schema_name}")
            with self.db.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    # Set search path to user schema
                    cursor.execute(f"SET search_path TO {schema_name}")

                    # Get all accounts with balances
                    cursor.execute(f"SELECT nama, tipe, saldo FROM {schema_name}.akun ORDER BY tipe, nama")

                    accounts = cursor.fetchall()
                    logger.info(f"Found {len(accounts)} accounts: {accounts}")

                    if not accounts:
                        accounts_message = f"""
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
                                'e-wallet': '📱',
                                'kartu kredit': '💳'
                            }.get(acc_type, '📋')

                            accounts_message += f"{emoji} *{acc_type.upper()}:*\n"
                            for account in acc_list:
                                accounts_message += f"• {account['nama']}: Rp {account['saldo']:,.0f}\n"
                            accounts_message += "\n"

                        # Total balance
                        accounts_message += f"💰 *Total Saldo:* Rp {total_balance:,.0f}\n\n"

                        # Quick actions
                        accounts_message += "*Aksi Cepat:*\n"
                        accounts_message += "• Ketik `nama_akun baru` untuk tambah akun\n"
                        accounts_message += "• Contoh: `mandiri bank` atau `gopay e-wallet`"

                    await update.message.reply_text(accounts_message, parse_mode='Markdown')

        except Exception as e:
            logger.error(f"Accounts error for user {user_id}: {e}")
            await update.message.reply_text("❌ Error mengambil data akun")


    async def handle_transaction_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle non-command messages - process transactions or account management."""
        message_text = update.message.text.strip()

        # Skip empty messages
        if not message_text:
            return

        # Check if message looks like account management
        if self._is_account_management(message_text):
            await self._handle_account_management(update, message_text)
        # Check if message looks like a transaction
        elif self._is_transaction_like(message_text):
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

    def _is_account_management(self, message: str) -> bool:
        """Check if message looks like account management."""
        message_lower = message.lower()

        # Account management patterns
        account_patterns = [
            'hapus', 'delete', 'remove',  # Remove account
            'bank', 'kas', 'e-wallet', 'kartu kredit'  # Add account with type
        ]

        # Check if it looks like "account_name account_type"
        words = message_lower.split()
        if len(words) == 2:
            account_name, account_type = words
            valid_types = ['kas', 'bank', 'e-wallet', 'kartu kredit', 'ewallet', 'kartu-kredit']
            if account_type in valid_types:
                return True

        # Check for remove patterns
        if message_lower.startswith(('hapus ', 'delete ', 'remove ')):
            return True

        return False

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

    async def _handle_account_management(self, update: Update, message: str):
        """Handle account management messages."""
        user = update.effective_user
        user_id = user.id
        schema_name = self.get_user_schema(user_id)
        message_lower = message.lower()

        try:
            # Ensure user schema exists
            if not self.ensure_user_schema(user_id):
                await update.message.reply_text("❌ Gagal mengakses database Anda")
                return

            # Handle account removal
            if message_lower.startswith(('hapus ', 'delete ', 'remove ')):
                account_name = message_lower.split(' ', 1)[1].strip()
                await self._remove_account_simple(update, schema_name, account_name)
                return

            # Handle account addition (format: "account_name account_type")
            words = message_lower.split()
            if len(words) == 2:
                account_name, account_type = words

                # Normalize account type
                type_mapping = {
                    'ewallet': 'e-wallet',
                    'kartu-kredit': 'kartu kredit',
                    'kartukredit': 'kartu kredit'
                }
                account_type = type_mapping.get(account_type, account_type)

                await self._add_account_simple(update, schema_name, account_name, account_type)
                return

            # If not recognized, show help
            await update.message.reply_text(
                "❌ Format tidak dikenali\n\n"
                "*Untuk menambah akun:* `nama_akun tipe`\n"
                "*Contoh:* `mandiri bank` atau `gopay e-wallet`\n\n"
                "*Untuk menghapus akun:* `hapus nama_akun`\n"
                "*Contoh:* `hapus mandiri`",
                parse_mode='Markdown'
            )

        except Exception as e:
            logger.error(f"Account management error for user {user_id}: {e}")
            await update.message.reply_text("❌ Error memproses permintaan akun")

    async def _add_account_simple(self, update: Update, schema_name: str, account_name: str, account_type: str):
        """Add account with simple interface."""
        user = update.effective_user
        user_id = user.id

        # Validate account type
        valid_types = ['kas', 'bank', 'e-wallet', 'kartu kredit']
        if account_type not in valid_types:
            await update.message.reply_text(
                f"❌ Tipe akun `{account_type}` tidak valid\n\n"
                f"Tipe yang tersedia: {', '.join(valid_types)}",
                parse_mode='Markdown'
            )
            return

        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    # Set search path to user schema
                    cursor.execute(f"SET search_path TO {schema_name}")

                    # Check if account already exists
                    cursor.execute(f"SELECT id FROM {schema_name}.akun WHERE nama = %s", (account_name,))
                    existing = cursor.fetchone()

                    if existing:
                        await update.message.reply_text(
                            f"❌ Akun `{account_name}` sudah ada!",
                            parse_mode='Markdown'
                        )
                        return

                    # Add new account
                    cursor.execute(f"""
                        INSERT INTO {schema_name}.akun (nama, tipe, saldo)
                        VALUES (%s, %s, 0)
                    """, (account_name, account_type))

                    conn.commit()

                    success_message = f"""
✅ *Akun Ditambahkan!*

📋 *{account_name}* ({account_type})
💰 Saldo: Rp 0

Sekarang bisa digunakan:
`gaji 50k {account_name}`
                    """

                    await update.message.reply_text(success_message, parse_mode='Markdown')
                    logger.info(f"User {user_id} added account: {account_name} ({account_type})")

        except Exception as e:
            logger.error(f"Add account error for user {user_id}: {e}")
            await update.message.reply_text("❌ Error menambah akun")

    async def _remove_account_simple(self, update: Update, schema_name: str, account_name: str):
        """Remove account with simple interface."""
        user = update.effective_user
        user_id = user.id

        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    # Set search path to user schema
                    cursor.execute(f"SET search_path TO {schema_name}")

                    # Check if account exists
                    cursor.execute(f"SELECT id FROM {schema_name}.akun WHERE nama = %s", (account_name,))
                    account = cursor.fetchone()

                    if not account:
                        await update.message.reply_text(
                            f"❌ Akun `{account_name}` tidak ditemukan!",
                            parse_mode='Markdown'
                        )
                        return

                    # Check if account has transactions
                    cursor.execute(f"SELECT COUNT(*) FROM {schema_name}.transaksi WHERE id_akun = %s", (account[0],))
                    transaction_count = cursor.fetchone()[0]

                    if transaction_count > 0:
                        await update.message.reply_text(
                            f"❌ Tidak bisa hapus akun `{account_name}`!\n\n"
                            f"Akun ini memiliki {transaction_count} transaksi.",
                            parse_mode='Markdown'
                        )
                        return

                    # Remove account
                    cursor.execute(f"DELETE FROM {schema_name}.akun WHERE nama = %s", (account_name,))
                    conn.commit()

                    success_message = f"""
✅ *Akun Dihapus!*

🗑️ `{account_name}` telah dihapus
                    """

                    await update.message.reply_text(success_message, parse_mode='Markdown')
                    logger.info(f"User {user_id} removed account: {account_name}")

        except Exception as e:
            logger.error(f"Remove account error for user {user_id}: {e}")
            await update.message.reply_text("❌ Error menghapus akun")
    
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
            parsed_data = self.parser.parse_transaction(transaction_input)

            # Insert to user-specific database
            logger.info(f"Parsed data for user {user_id}: {parsed_data}")
            transaction_id = self._insert_user_transaction(schema_name, parsed_data)
            logger.info(f"Transaction {transaction_id} inserted for user {user_id} in schema {schema_name}")

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

    def _get_user_monthly_summary(self, schema_name: str, year: int, month: int) -> Dict[str, Any]:
        """Get monthly summary for specific user schema."""
        try:
            with self.db.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    # Set search path to user schema
                    cursor.execute(f"SET search_path TO {schema_name}")

                    # Get summary by category
                    cursor.execute(f"""
                        SELECT
                            t.tipe,
                            t.kategori,
                            SUM(t.nominal) as total,
                            COUNT(*) as jumlah_transaksi
                        FROM {schema_name}.transaksi t
                        WHERE EXTRACT(YEAR FROM t.waktu) = %s
                          AND EXTRACT(MONTH FROM t.waktu) = %s
                        GROUP BY t.tipe, t.kategori
                        ORDER BY t.tipe, total DESC
                    """, (year, month))
                    category_summary = cursor.fetchall()

                    # Get totals
                    cursor.execute(f"""
                        SELECT
                            SUM(CASE WHEN tipe = 'pemasukan' THEN nominal ELSE 0 END) as total_pemasukan,
                            SUM(CASE WHEN tipe = 'pengeluaran' THEN nominal ELSE 0 END) as total_pengeluaran,
                            COUNT(*) as total_transaksi
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
                        return result[0]

                    # Auto-detect account type if not provided
                    if not account_type:
                        account_type = self._detect_account_type(account_name)

                    # Create new account
                    cursor.execute(f"""
                        INSERT INTO {schema_name}.akun (nama, tipe, saldo)
                        VALUES (%s, %s, 0)
                        RETURNING id
                    """, (account_name, account_type))
                    new_id = cursor.fetchone()[0]
                    conn.commit()

                    logger.info(f"Created new account '{account_name}' ({account_type}) for schema {schema_name}")
                    print(f"DEBUG: Created account '{account_name}' with type '{account_type}'")
                    return new_id

        except Exception as e:
            logger.error(f"Error in get_or_create_user_account for {schema_name}: {e}")
            raise

    def _detect_account_type(self, account_name: str) -> str:
        """Detect account type based on account name."""
        name_lower = account_name.lower()
        print(f"DEBUG: Detecting account type for '{account_name}' (lowercase: '{name_lower}')")

        # Specific bank detection - if it's a specific bank name, it's a bank account
        specific_banks = [
            'bca', 'bri', 'bni', 'mandiri', 'btn', 'cimb', 'danamon', 'mega',
            'permata', 'panin', 'bukopin', 'maybank', 'btn', 'bjb', 'bsi',
            'btpn', 'jenius', 'neo', 'seabank', 'uob', 'ocbc', 'dbs', 'hsbc'
        ]
        for bank in specific_banks:
            if bank in name_lower:
                print(f"DEBUG: Detected specific bank '{bank}' in '{name_lower}', returning 'bank'")
                return 'bank'

        # Generic bank keywords
        bank_keywords = ['bank', 'rekening', 'tabungan']
        if any(keyword in name_lower for keyword in bank_keywords):
            print(f"DEBUG: Detected generic bank keyword in '{name_lower}', returning 'bank'")
            return 'bank'

        # E-wallet detection
        ewallet_keywords = ['dana', 'gopay', 'ovo', 'linkaja', 'shopeepay', 'sakuku', 'gopaydriver']
        if any(keyword in name_lower for keyword in ewallet_keywords):
            print(f"DEBUG: Detected e-wallet in '{name_lower}', returning 'e-wallet'")
            return 'e-wallet'

        # Credit card detection
        credit_keywords = ['kartu kredit', 'credit', 'cc', 'visa', 'mastercard', 'amex']
        if any(keyword in name_lower for keyword in credit_keywords):
            print(f"DEBUG: Detected credit card in '{name_lower}', returning 'kartu kredit'")
            return 'kartu kredit'

        # Cash detection
        cash_keywords = ['cash', 'tunai', 'uang']
        if any(keyword in name_lower for keyword in cash_keywords):
            print(f"DEBUG: Detected cash in '{name_lower}', returning 'kas'")
            return 'kas'

        # Default to kas (cash)
        print(f"DEBUG: No specific type detected for '{name_lower}', defaulting to 'kas'")
        return 'kas'

    def _insert_user_transaction(self, schema_name: str, transaksi_data: Dict[str, Any]) -> int:
        """Insert transaction into user schema."""
        try:
            # Get or create account
            akun_id = self._get_or_create_user_account(schema_name, transaksi_data['akun'])

            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    # Set search path to user schema
                    cursor.execute(f"SET search_path TO {schema_name}")

                    cursor.execute(f"""
                        INSERT INTO {schema_name}.transaksi
                        (tipe, nominal, id_akun, kategori, catatan, waktu)
                        VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                        RETURNING id
                    """, (
                        transaksi_data['tipe'],
                        transaksi_data['nominal'],
                        akun_id,
                        transaksi_data['kategori'],
                        transaksi_data['catatan']
                    ))
                    transaksi_id = cursor.fetchone()[0]

                    # Update account balance
                    balance_change = transaksi_data['nominal']
                    if transaksi_data['tipe'] == 'pengeluaran':
                        balance_change = -balance_change

                    cursor.execute(f"UPDATE {schema_name}.akun SET saldo = saldo + %s WHERE id = %s", (balance_change, akun_id))

                    conn.commit()

                    logger.info(f"Inserted transaction ID {transaksi_id} for user schema {schema_name}")
                    return transaksi_id

        except Exception as e:
            logger.error(f"Error inserting transaction for {schema_name}: {e}")
            raise
    
    async def setup_bot_commands(self):
        """Setup simplified bot commands menu."""
        commands = [
            BotCommand("start", "Mulai menggunakan CashMate"),
            BotCommand("help", "Bantuan dan panduan"),
            BotCommand("accounts", "Lihat akun & saldo"),
            BotCommand("summary", "Ringkasan bulanan"),
            BotCommand("recent", "Transaksi terakhir"),
            BotCommand("input", "Catat transaksi manual"),
            BotCommand("test", "Test koneksi sistem"),
        ]

        await self.application.bot.set_my_commands(commands)
        logger.info("Simplified bot commands menu setup completed")
    
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