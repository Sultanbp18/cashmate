"""
Pytest configuration and fixtures for CashMate tests.
"""

import os
import sys
import pytest
from pathlib import Path

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

@pytest.fixture(scope="session")
def test_env():
    """Set up test environment variables."""
    # Use test database configuration
    os.environ.setdefault('POSTGRES_HOST', 'localhost')
    os.environ.setdefault('POSTGRES_DB', 'cashmate_test')
    os.environ.setdefault('POSTGRES_USER', 'cashmate_test')
    os.environ.setdefault('POSTGRES_PASSWORD', 'test_password')
    os.environ.setdefault('DEBUG', 'true')

    # Mock AI API key for tests
    os.environ.setdefault('GEMINI_API_KEY', 'test_key')

    # Mock Telegram token for tests
    os.environ.setdefault('TELEGRAM_BOT_TOKEN', 'test_token')

    yield

    # Cleanup after tests
    # Note: In real implementation, you might want to clean up test data

@pytest.fixture
def mock_db():
    """Mock database for testing."""
    # This would be implemented with actual mocking
    # For now, return None
    return None

@pytest.fixture
def sample_transaction():
    """Sample transaction data for testing."""
    return {
        'tipe': 'pengeluaran',
        'nominal': 15000,
        'akun': 'cash',
        'kategori': 'makanan',
        'catatan': 'Test transaction'
    }

@pytest.fixture
def sample_user_id():
    """Sample user ID for testing."""
    return 123456789