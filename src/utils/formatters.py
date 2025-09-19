"""
Formatting utilities for CashMate application.
"""

def format_currency(amount: float) -> str:
    """Format currency to Indonesian Rupiah."""
    return f"Rp {amount:,.0f}"