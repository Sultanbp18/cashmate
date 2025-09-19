"""
Configuration settings for CashMate application.
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ========================================
# DATABASE CONFIGURATION
# ========================================
DATABASE_URL = os.getenv('DATABASE_URL')
POSTGRES_HOST = os.getenv('POSTGRES_HOST', 'localhost')
POSTGRES_PORT = os.getenv('POSTGRES_PORT', '5432')
POSTGRES_DB = os.getenv('POSTGRES_DB', 'cashmate')
POSTGRES_USER = os.getenv('POSTGRES_USER')
POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD')

# ========================================
# AI CONFIGURATION
# ========================================
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

# ========================================
# TELEGRAM BOT CONFIGURATION
# ========================================
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

# ========================================
# APPLICATION CONFIGURATION
# ========================================
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

# ========================================
# VALIDATION
# ========================================
def validate_config():
    """Validate required configuration settings."""
    errors = []

    # Check database configuration
    if not DATABASE_URL and not all([POSTGRES_USER, POSTGRES_PASSWORD]):
        errors.append("Database configuration missing. Set DATABASE_URL or POSTGRES_* variables")

    # Check AI configuration
    if not GEMINI_API_KEY:
        errors.append("GEMINI_API_KEY is required for AI transaction parsing")

    # Check Telegram configuration
    if not TELEGRAM_BOT_TOKEN:
        errors.append("TELEGRAM_BOT_TOKEN is required for bot functionality")

    if errors:
        raise ValueError("Configuration errors:\n" + "\n".join(f"- {error}" for error in errors))

    return True

# Validate configuration on import
validate_config()