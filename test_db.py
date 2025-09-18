#!/usr/bin/env python3
"""
Test script to debug database connection and schema issues.
"""

import os
import sys
from dotenv import load_dotenv
from db import get_db

# Load environment variables
load_dotenv()

def test_database_connection():
    """Test basic database connection."""
    print("🔍 Testing database connection...")

    try:
        db = get_db()
        success = db.test_connection()
        if success:
            print("✅ Database connection: OK")
            return True
        else:
            print("❌ Database connection: Failed")
            return False
    except Exception as e:
        print(f"❌ Database connection error: {e}")
        return False

def test_user_schema(user_id: int):
    """Test user schema creation and access."""
    print(f"\n🔍 Testing user schema for user {user_id}...")

    try:
        db = get_db()
        schema_name = f"user_{user_id}"

        with db.get_connection() as conn:
            with conn.cursor() as cursor:
                # Check if schema exists
                cursor.execute("SELECT EXISTS(SELECT 1 FROM information_schema.schemata WHERE schema_name = %s)", (schema_name,))
                schema_exists = cursor.fetchone()[0]

                if not schema_exists:
                    print(f"📝 Creating schema {schema_name}...")
                    cursor.execute(f"CREATE SCHEMA {schema_name}")
                    print(f"✅ Schema {schema_name} created")
                else:
                    print(f"✅ Schema {schema_name} already exists")

                # Create tables if they don't exist
                print("📝 Ensuring tables exist...")

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

                # Create default accounts
                cursor.execute(f"""
                    INSERT INTO {schema_name}.akun (nama, tipe, saldo)
                    VALUES
                        ('cash', 'kas', 0),
                        ('bni', 'bank', 0),
                        ('dana', 'e-wallet', 0)
                    ON CONFLICT (nama) DO NOTHING
                """)

                conn.commit()
                print("✅ Tables and default accounts created")

                # Test data retrieval
                print("\n🔍 Testing data retrieval...")

                # Check accounts
                cursor.execute(f"SELECT COUNT(*) FROM {schema_name}.akun")
                account_count = cursor.fetchone()[0]
                print(f"📊 Accounts found: {account_count}")

                # Check transactions
                cursor.execute(f"SELECT COUNT(*) FROM {schema_name}.transaksi")
                transaction_count = cursor.fetchone()[0]
                print(f"📊 Transactions found: {transaction_count}")

                # Get account balances
                cursor.execute(f"SELECT nama, saldo FROM {schema_name}.akun ORDER BY nama")
                accounts = cursor.fetchall()
                print("💳 Account balances:")
                for account in accounts:
                    print(f"  • {account[0]}: Rp {account[1]:,.0f}")

                return True

    except Exception as e:
        print(f"❌ Schema test error: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main test function."""
    print("🧪 CashMate Database Test")
    print("=" * 50)

    # Test basic connection
    if not test_database_connection():
        print("\n❌ Cannot proceed without database connection")
        sys.exit(1)

    # Test user schema (use a test user ID)
    test_user_id = 123456789  # Test user ID
    if test_user_schema(test_user_id):
        print(f"\n✅ All tests passed for user {test_user_id}")
    else:
        print(f"\n❌ Tests failed for user {test_user_id}")

    print("\n🏁 Test completed")

if __name__ == "__main__":
    main()