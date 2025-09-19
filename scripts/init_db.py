#!/usr/bin/env python3
"""
Database initialization script for CashMate.
Creates necessary schemas and tables.
"""

import os
import sys
import logging
from pathlib import Path

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from src.core.database import DatabaseManager
from src.config import DATABASE_URL, POSTGRES_HOST, POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def init_database():
    """Initialize database with required schemas and tables."""
    try:
        logger.info("Initializing CashMate database...")

        # Initialize database manager
        db = DatabaseManager()

        # Test connection
        if not db.test_connection():
            logger.error("Failed to connect to database")
            return False

        logger.info("Database connection successful")

        # Note: In the current multi-user schema approach,
        # schemas are created automatically when users first interact with the bot.
        # This script mainly serves as a connection test and future extension point.

        logger.info("Database initialization completed successfully")
        logger.info("Note: User schemas will be created automatically on first use")

        return True

    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        return False

def create_admin_schema():
    """Create admin schema for system-wide operations (future use)."""
    try:
        logger.info("Creating admin schema...")

        db = DatabaseManager()

        with db.get_connection() as conn:
            with conn.cursor() as cursor:
                # Create admin schema if it doesn't exist
                cursor.execute("CREATE SCHEMA IF NOT EXISTS admin")

                # Create system tables (for future use)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS admin.system_info (
                        key VARCHAR(100) PRIMARY KEY,
                        value TEXT,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                # Insert version info
                cursor.execute("""
                    INSERT INTO admin.system_info (key, value)
                    VALUES ('version', '1.0.0')
                    ON CONFLICT (key) DO UPDATE SET
                        value = EXCLUDED.value,
                        updated_at = CURRENT_TIMESTAMP
                """)

                conn.commit()

        logger.info("Admin schema created successfully")
        return True

    except Exception as e:
        logger.error(f"Failed to create admin schema: {e}")
        return False

def test_database_connection():
    """Test database connection and permissions."""
    try:
        logger.info("Testing database connection...")

        db = DatabaseManager()

        if db.test_connection():
            logger.info("✅ Database connection test passed")

            # Test basic operations
            with db.get_connection() as conn:
                with conn.cursor() as cursor:
                    # Test schema creation permission
                    cursor.execute("CREATE SCHEMA IF NOT EXISTS test_schema")
                    cursor.execute("DROP SCHEMA IF EXISTS test_schema CASCADE")
                    conn.commit()

            logger.info("✅ Database permissions test passed")
            return True
        else:
            logger.error("❌ Database connection test failed")
            return False

    except Exception as e:
        logger.error(f"❌ Database test failed: {e}")
        return False

def show_database_info():
    """Show database information and status."""
    try:
        logger.info("Database Information:")
        logger.info(f"Host: {POSTGRES_HOST}")
        logger.info(f"Database: {POSTGRES_DB}")
        logger.info(f"User: {POSTGRES_USER}")

        db = DatabaseManager()

        with db.get_connection() as conn:
            with conn.cursor() as cursor:
                # Get PostgreSQL version
                cursor.execute("SELECT version()")
                version = cursor.fetchone()[0]
                logger.info(f"PostgreSQL Version: {version}")

                # List existing schemas
                cursor.execute("""
                    SELECT schema_name
                    FROM information_schema.schemata
                    WHERE schema_name NOT LIKE 'pg_%'
                      AND schema_name != 'information_schema'
                    ORDER BY schema_name
                """)
                schemas = cursor.fetchall()

                logger.info("Existing schemas:")
                for schema in schemas:
                    schema_name = schema[0]
                    logger.info(f"  - {schema_name}")

                    # Count tables in schema
                    cursor.execute("""
                        SELECT COUNT(*)
                        FROM information_schema.tables
                        WHERE table_schema = %s
                    """, (schema_name,))
                    table_count = cursor.fetchone()[0]
                    logger.info(f"    Tables: {table_count}")

    except Exception as e:
        logger.error(f"Failed to get database info: {e}")

def main():
    """Main initialization function."""
    logger.info("CashMate Database Initialization Script")
    logger.info("=" * 50)

    # Test connection first
    if not test_database_connection():
        logger.error("Database connection failed. Please check your configuration.")
        sys.exit(1)

    # Show database info
    show_database_info()

    # Initialize database
    if init_database():
        logger.info("✅ Database initialization completed successfully")
    else:
        logger.error("❌ Database initialization failed")
        sys.exit(1)

    # Create admin schema (optional)
    if create_admin_schema():
        logger.info("✅ Admin schema created successfully")
    else:
        logger.warning("⚠️  Admin schema creation failed (non-critical)")

    logger.info("=" * 50)
    logger.info("CashMate is ready to use!")
    logger.info("User schemas will be created automatically when users first interact with the bot.")

if __name__ == "__main__":
    main()