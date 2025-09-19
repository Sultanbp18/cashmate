"""
Validation utilities for CashMate application.
"""

def validate_month(month: int) -> bool:
    """Validate month is between 1-12."""
    return 1 <= month <= 12