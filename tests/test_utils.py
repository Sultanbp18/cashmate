"""
Tests for CashMate utility functions.
"""

import pytest
from src.utils.formatters import format_currency
from src.utils.validators import validate_month
from src.utils.helpers import get_current_month, clean_transaction_input

class TestFormatters:
    """Test currency formatting functions."""

    def test_format_currency(self):
        """Test currency formatting."""
        assert format_currency(15000) == "Rp 15,000"
        assert format_currency(1500000) == "Rp 1,500,000"
        assert format_currency(0) == "Rp 0"
        assert format_currency(1234567) == "Rp 1,234,567"

    def test_format_currency_float(self):
        """Test currency formatting with float values."""
        assert format_currency(15000.5) == "Rp 15,001"  # Rounded
        assert format_currency(15000.4) == "Rp 15,000"  # Rounded

class TestValidators:
    """Test validation functions."""

    def test_validate_month_valid(self):
        """Test valid month validation."""
        for month in range(1, 13):
            assert validate_month(month) is True

    def test_validate_month_invalid(self):
        """Test invalid month validation."""
        invalid_months = [0, 13, 15, -1, 100]
        for month in invalid_months:
            assert validate_month(month) is False

class TestHelpers:
    """Test helper functions."""

    def test_get_current_month(self):
        """Test getting current month."""
        year, month = get_current_month()
        assert isinstance(year, int)
        assert isinstance(month, int)
        assert 1 <= month <= 12
        assert year >= 2024  # Assuming current year

    def test_clean_transaction_input(self):
        """Test transaction input cleaning."""
        assert clean_transaction_input("bakso 15k") == "bakso 15k"
        assert clean_transaction_input("/input bakso 15k") == "bakso 15k"
        assert clean_transaction_input("  bakso 15k  ") == "bakso 15k"
        assert clean_transaction_input("/input  bakso 15k  ") == "bakso 15k"

    def test_clean_transaction_input_empty(self):
        """Test cleaning empty input."""
        assert clean_transaction_input("") == ""
        assert clean_transaction_input("   ") == ""
        assert clean_transaction_input("/input") == ""
        assert clean_transaction_input("/input   ") == ""