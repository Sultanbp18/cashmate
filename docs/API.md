# CashMate API Documentation

## Overview

CashMate provides a programmatic interface for managing personal finances through various services and utilities.

## Core Components

### Database Manager (`src.core.database`)

```python
from src.core.database import get_db

db = get_db()

# Test connection
db.test_connection()

# Get monthly summary
summary = db.get_monthly_summary(year=2024, month=12)

# Insert transaction
transaction_data = {
    'tipe': 'pengeluaran',
    'nominal': 50000,
    'akun': 'cash',
    'kategori': 'makanan',
    'catatan': 'Bakso'
}
transaction_id = db.insert_transaksi(transaction_data)
```

### NLP Processor (`src.services.nlp_processor`)

```python
from src.services.nlp_processor import get_parser

parser = get_parser()

# Parse transaction text
parsed_data = parser.parse_transaction("bakso 15k cash")
# Returns: {'tipe': 'pengeluaran', 'nominal': 15000, 'akun': 'cash', 'kategori': 'makanan', 'catatan': 'bakso'}
```

### Expense Manager (`src.services.expense_manager`)

```python
from src.services.expense_manager import ExpenseManager

expense_mgr = ExpenseManager()

# Process transaction for user
result = expense_mgr.process_transaction(user_id=123, transaction_data=parsed_data)

# Get user accounts
accounts = expense_mgr.get_user_accounts(user_id=123)

# Get monthly summary
summary = expense_mgr.get_monthly_summary(user_id=123, year=2024, month=12)
```

### Report Generator (`src.services.report_generator`)

```python
from src.services.report_generator import ReportGenerator

report_gen = ReportGenerator()

# Generate monthly report
monthly_report = report_gen.generate_monthly_report(user_id=123, year=2024, month=12)

# Generate yearly report
yearly_report = report_gen.generate_yearly_report(user_id=123, year=2024)

# Generate account report
account_report = report_gen.generate_account_report(user_id=123, account_name='cash')
```

## Utility Functions

### Formatters (`src.utils.formatters`)

```python
from src.utils.formatters import format_currency

# Format currency
formatted = format_currency(15000)  # Returns: "Rp 15,000"
```

### Validators (`src.utils.validators`)

```python
from src.utils.validators import validate_month

# Validate month
is_valid = validate_month(12)  # Returns: True
is_valid = validate_month(13)  # Returns: False
```

### Helpers (`src.utils.helpers`)

```python
from src.utils.helpers import get_current_month, clean_transaction_input

# Get current month
year, month = get_current_month()  # Returns: (2024, 12)

# Clean transaction input
cleaned = clean_transaction_input("/input bakso 15k")  # Returns: "bakso 15k"
```

## Configuration

The application uses environment variables for configuration:

```python
from src.config import (
    DATABASE_URL, POSTGRES_HOST, POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD,
    GEMINI_API_KEY, TELEGRAM_BOT_TOKEN, DEBUG
)
```

## Error Handling

All services include comprehensive error handling and logging. Common exceptions:

- `ValueError`: Invalid input data
- `ConnectionError`: Database connection issues
- `Exception`: General processing errors

## Data Models

### Transaction Data Structure

```python
transaction_data = {
    'tipe': 'pemasukan|pengeluaran|transfer',
    'nominal': float,  # Amount
    'akun': str,       # Account name
    'akun_asal': str,  # Source account (for transfers)
    'akun_tujuan': str, # Destination account (for transfers)
    'kategori': str,   # Category
    'catatan': str     # Notes
}
```

### Account Data Structure

```python
account_data = {
    'nama': str,       # Account name
    'tipe': str,       # Account type ('kas', 'bank', 'e-wallet')
    'saldo': float     # Current balance
}
```

## Testing

Run tests using pytest:

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_nlp_processor.py

# Run with coverage
pytest --cov=src