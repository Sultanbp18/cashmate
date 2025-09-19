"""
Start command handler for CashMate Telegram bot.
"""

import logging
from telegram import Update
from telegram.ext import ContextTypes

from ...core.database import get_db
from ...services.nlp_processor import get_parser

logger = logging.getLogger(__name__)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command with auto-setup."""
    user = update.effective_user
    user_id = user.id

    # Get services
    db = get_db()
    parser = get_parser()

    # Auto-setup user database
    setup_success = _ensure_user_schema(db, user_id)

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

def _ensure_user_schema(db, user_id: int) -> bool:
    """Ensure user schema exists and is properly set up."""
    schema_name = f"user_{user_id}"

    try:
        with db.get_connection() as conn:
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
                    _create_user_tables(cursor, schema_name)

                    # Create default accounts for user
                    _create_default_accounts(cursor, schema_name)

                    conn.commit()
                    logger.info(f"Successfully created schema and tables for user {user_id}")
                    return True
                else:
                    logger.info(f"Schema {schema_name} already exists for user {user_id}")
                    # Check if tables exist, create if missing
                    _ensure_user_tables_exist(cursor, schema_name)
                    conn.commit()
                    return True

    except Exception as e:
        logger.error(f"Error ensuring user schema for {user_id}: {e}")
        return False

def _create_user_tables(cursor, schema_name: str):
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

def _create_default_accounts(cursor, schema_name: str):
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

def _ensure_user_tables_exist(cursor, schema_name: str):
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
        _create_user_tables(cursor, schema_name)
        _create_default_accounts(cursor, schema_name)