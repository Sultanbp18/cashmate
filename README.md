# 🏦 CashMate - Personal Money Tracker

**CashMate** is an AI-powered personal money tracker that leverages Google's Gemini AI to parse natural language transaction inputs and store them in PostgreSQL. Perfect for tracking expenses with Indonesian language support.

## ✨ Key Features

- 🤖 **AI Transaction Parsing** - Natural language input: `"bakso 15k pake cash"`
- 💾 **PostgreSQL Integration** - External database support (Aiven, AWS RDS, Heroku)
- 📊 **Smart Categorization** - Auto-categorize transactions
- 💳 **Multi-Account Support** - Cash, bank, e-wallets (Dana, GoPay, OVO)
- 📈 **Monthly Reports** - Detailed summaries by category
- 🚫 **Balance Protection** - Prevents negative balances with clear error messages
- 🏗️ **Modular Architecture** - Clean, scalable codebase structure
- 🐳 **Docker Ready** - Easy deployment
- 📚 **Well Documented** - Comprehensive API and usage documentation

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- PostgreSQL database (local/external)
- Google Gemini AI API key
- Telegram Bot Token

### 1. Setup
```bash
git clone <repository-url>
cd cashmate
pip install -r requirements.txt
cp .env.example .env
```

### 2. Configure Environment
```env
# Database Configuration
DATABASE_URL=postgresql://user:pass@host:port/database
# OR
POSTGRES_HOST=localhost
POSTGRES_DB=cashmate
POSTGRES_USER=username
POSTGRES_PASSWORD=password

# AI Configuration
GEMINI_API_KEY=your_gemini_api_key

# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
```

### 3. Run CashMate
```bash
# Using the new modular structure
python main.py

# Or directly
python -m src.bot.main

# Docker deployment
docker build -t cashmate .
docker run --env-file .env cashmate
```

## 📖 Usage Examples

### 🤖 Telegram Bot (Recommended)
```
User: /start
Bot: Welcome! Send transactions like: bakso 15k cash

User: bakso 15k pake cash
Bot: ✅ Expense recorded: Rp 15,000, Cash, Food

User: transfer bca ke dana 50k
Bot: 🔄 Transfer successful: Rp 50,000 from bca to dana

User: beli laptop 20jt cash
Bot: ❌ Transaksi Gagal - Saldo Tidak Cukup
      Saldo tersedia: Rp 5,000,000, Dibutuhkan: Rp 20,000,000

User: tarik tunai dari bca 5jt
Bot: 🔄 Transfer successful: Rp 5,000,000 from bca to cash

User: /summary
Bot: 📊 Monthly Summary: Income +Rp 0, Expenses -Rp 15,000

*Note: Transfer transactions are excluded from income/expense totals and only affect account balances.*

User: /recent
Bot: 📄 Recent transactions with details
```

### 💻 CLI Interface (Removed)
The CLI interface has been removed to focus on the Telegram bot. Use the Telegram bot for all interactions.

### 🚀 Quick Commands (Both Interfaces)
```bash
# Telegram & CLI
/input <transaction>  # Add transaction
/summary             # Monthly summary
/recent              # Recent transactions
/help               # Show menu
/start              # Bot welcome (Telegram only)
/accounts           # Show account balances
/test               # Test connections
```

### 🔄 Transfer Commands
```bash
# Natural language transfers
"transfer bca ke dana 50k"     # Transfer between accounts
"tarik tunai dari bca 5jt"     # Withdraw to cash
"pindah dari mandiri ke bca 2jt"  # Transfer between banks
```

## ️ Database Setup Guide

### Current Implementation: Multi-User Schema Approach
- **Database**: Any name (defaultdb, postgres, cashmate)
- **Schema**: `user_{telegram_user_id}` (auto-created per user)
- **Tables**: `user_123.akun`, `user_123.transaksi`

**Benefits:**
- ✅ **User Isolation**: Each Telegram user has their own schema
- ✅ **Auto Setup**: Schemas created automatically on first use
- ✅ **No Manual Setup**: Just provide database connection
- ✅ **Flexible**: Works with any PostgreSQL provider

### Setup Options

#### Option 1: External Database (Recommended)
**For Aiven, AWS RDS, Railway, Heroku, etc.**

```bash
# 1. Use provider's default database
DATABASE_URL=postgresql://user:pass@host:port/defaultdb

# 2. Run initialization
psql "your_connection_string" -f init.sql

# 3. Start CashMate  
python main.py
```

**Examples:**
```env
# Aiven
DATABASE_URL=postgresql://avnadmin:pass@service.aivencloud.com:12345/defaultdb?sslmode=require

# AWS RDS  
DATABASE_URL=postgresql://postgres:pass@rds-endpoint:5432/postgres

# Railway
DATABASE_URL=postgresql://postgres:pass@containers.railway.app:1234/railway
```

#### Option 2: Local Development
```bash
# Using Docker (creates local PostgreSQL)
docker-compose up -d

# Manual setup
createdb cashmate
psql cashmate -f init.sql
python main.py
```

### Database Structure
```
Database: [any name]
├── Schema: cashmate
│   ├── Table: akun (accounts)
│   └── Table: transaksi (transactions)
```

### Verification
```bash
# Test connection
python main.py "6"

# Check schema exists
psql "connection_string" -c "SELECT schema_name FROM information_schema.schemata WHERE schema_name = 'cashmate';"

# Test transaction
python main.py "/input test 1000 cash"
```

## 🐳 Docker Deployment

### Simple Docker Setup
```bash
# Build the image
docker build -t cashmate .

# Run the Telegram bot
docker run --env-file .env cashmate
```

### Production Deployment
```bash
# Build optimized image
docker build --no-cache -t cashmate .

# Run in background
docker run -d --name cashmate-bot --env-file .env --restart unless-stopped cashmate

# View logs
docker logs -f cashmate-bot
```

## 🤖 AI Transaction Examples

The Gemini AI understands Indonesian natural language:

| Input | Parsed Output |
|-------|---------------|
| `bakso 15k pake cash` | Expense: Rp 15,000, Cash, Food |
| `gojek ke kantor 20rb` | Expense: Rp 20,000, Cash, Transport |
| `gaji bulan ini 5jt ke bca` | Income: Rp 5,000,000, BCA, Salary |
| `bonus 1233 ke shopee` | Income: Rp 1,233, ShopeePay, Salary |
| `beli buku 50rb dana` | Expense: Rp 50,000, Dana, Shopping |
| `belanja di shopee 50k` | Expense: Rp 50,000, Cash, Shopping |
| `belanja di shopee 50k pake shopeepay` | Expense: Rp 50,000, ShopeePay, Shopping |
| `transfer bca ke dana 50k` | Transfer: Rp 50,000, BCA → Dana |
| `tarik tunai dari bca 5jt` | Transfer: Rp 5,000,000, BCA → Cash |

**Amount Formats:**
- `15k` → Rp 15,000
- `500rb` → Rp 500,000  
- `2jt` → Rp 2,000,000

## 🔧 Configuration

### Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `DATABASE_URL` | Complete connection string | `postgresql://user:pass@host:port/db` |
| `POSTGRES_HOST` | Individual DB host | `localhost` |
| `POSTGRES_DB` | Database name | `defaultdb` |
| `POSTGRES_USER` | Username | `postgres` |
| `POSTGRES_PASSWORD` | Password | `password` |
| `GEMINI_API_KEY` | Google Gemini API key | Required |
| `DEBUG` | Enable debug logging | `False` |

### Getting Gemini API Key
1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create new API key
3. Add to `.env` file

## 🔍 Troubleshooting

### Connection Issues
```bash
# Test database connection
python -c "from db import get_db; db = get_db(); db.test_connection(); print('Database OK')"

# Test AI parser
python -c "from ai_parser import get_parser; p = get_parser(); print('AI Parser OK')"

# Check user schemas (replace USER_ID with actual Telegram user ID)
psql "connection_string" -c "\dt user_123.*"
```

### Common Fixes
- **Database connection failed**: Check `DATABASE_URL` in `.env`
- **Schema not found**: Schemas are created automatically on first use
- **AI parser errors**: Verify `GEMINI_API_KEY` and internet connection
- **Permission denied**: Grant schema permissions to database user
- **AI Model Overload (503)**: Gemini AI is temporarily busy, system will use fallback parser
- **Transfer parsing errors**: Use simple formats like `transfer bca ke dana 50k`
- **Account not found**: Accounts are created automatically on first use
- **Multiple bot instances**: Stop other bot processes before starting new one

### Telegram Bot Issues
- **Conflict Error**: "terminated by other getUpdates request" means multiple bot instances running
- **Solution**: Stop all other bot processes first with `pkill -f telegram_bot.py`
- **Docker**: Use `docker stop <container_id>` if running in container
- **Process Check**: Run `ps aux | grep telegram_bot` to find running instances
- **Wait Time**: Wait 30 seconds after stopping before restarting

## 📁 Project Structure

```
cashmate/
├── src/                    # Source code
│   ├── __init__.py
│   ├── config.py          # Configuration management
│   ├── bot/               # Telegram bot package
│   │   ├── __init__.py
│   │   ├── main.py        # Bot entry point
│   │   ├── handlers/      # Command handlers
│   │   │   ├── __init__.py
│   │   │   ├── start.py   # /start command
│   │   │   ├── expense.py # Transaction handling
│   │   │   ├── report.py  # Report commands
│   │   │   └── settings.py # Settings & help
│   │   └── keyboards.py   # Bot keyboards/menus
│   ├── core/              # Core functionality
│   │   ├── __init__.py
│   │   ├── database.py    # Database operations
│   │   └── models.py      # Data models & schemas
│   ├── services/          # Business logic services
│   │   ├── __init__.py
│   │   ├── nlp_processor.py   # AI transaction parsing
│   │   ├── expense_manager.py # Expense operations
│   │   └── report_generator.py # Report generation
│   └── utils/             # Utility functions
│       ├── __init__.py
│       ├── helpers.py     # Helper functions
│       ├── formatters.py  # Formatting utilities
│       └── validators.py  # Validation functions
├── tests/                 # Test suite
│   ├── __init__.py
│   ├── conftest.py        # Test configuration
│   └── test_utils.py      # Utility tests
├── docs/                  # Documentation
│   ├── API.md            # API documentation
│   ├── SETUP.md          # Setup guide
│   └── USAGE.md          # Usage guide
├── scripts/               # Utility scripts
│   ├── deploy.sh         # Deployment script
│   └── init_db.py        # Database initialization
├── main.py               # Application entry point
├── pyproject.toml        # Python project configuration
├── requirements.txt      # Production dependencies
├── requirements-dev.txt  # Development dependencies
├── .env.example          # Environment template
├── Dockerfile            # Container configuration
└── README.md            # This documentation
```

## 🛠️ Development

### Project Structure Overview

The codebase is organized into modular packages:

- **`src.bot`**: Telegram bot implementation with command handlers
- **`src.core`**: Database operations and data models
- **`src.services`**: Business logic (AI parsing, expense management, reporting)
- **`src.utils`**: Utility functions and helpers
- **`tests`**: Test suite with fixtures and test cases

### Adding Features

1. **New Bot Commands**: Add handlers in `src/bot/handlers/`
2. **Database Changes**: Update models in `src/core/models.py` and operations in `src/core/database.py`
3. **Business Logic**: Extend services in `src/services/`
4. **AI Categories**: Modify prompts in `src/services/nlp_processor.py`

### API Usage

```python
# Import from modular structure
from src.core.database import get_db
from src.services.nlp_processor import get_parser
from src.services.expense_manager import ExpenseManager
from src.services.report_generator import ReportGenerator

# Parse transaction
parser = get_parser()
data = parser.parse_transaction("bakso 15k cash")

# Process transaction for user
expense_mgr = ExpenseManager()
result = expense_mgr.process_transaction(user_id=123, transaction_data=data)

# Generate reports
report_gen = ReportGenerator()
monthly_report = report_gen.generate_monthly_report(user_id=123)
```

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_utils.py

# Run with coverage
pytest --cov=src --cov-report=html
```

### Code Quality

```bash
# Format code
black src/
isort src/

# Lint code
flake8 src/
mypy src/
```

## 📊 Performance & Security

- **Connection pooling** with SQLAlchemy
- **Prepared statements** prevent SQL injection
- **SSL/TLS support** for external databases
- **Input validation** on all user inputs
- **Error handling** with proper logging
- **Environment-based configuration**

## 🤝 Contributing

1. Fork repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## 📄 License

MIT License - see LICENSE file for details.

---

**CashMate** - Making personal finance tracking as easy as chatting! 💬💰

For detailed setup guides and troubleshooting, see the inline documentation in each file.