# 🏦 CashMate - Personal Money Tracker

**CashMate** is an AI-powered personal money tracker that leverages Google's Gemini AI to parse natural language transaction inputs and store them in PostgreSQL. Perfect for tracking expenses with Indonesian language support.

## ✨ Key Features

- 🤖 **AI Transaction Parsing** - Natural language input: `"bakso 15k pake cash"`
- 💾 **PostgreSQL Integration** - External database support (Aiven, AWS RDS, Heroku)
- 📊 **Smart Categorization** - Auto-categorize transactions 
- 💳 **Multi-Account Support** - Cash, bank, e-wallets (Dana, GoPay, OVO)
- 📈 **Monthly Reports** - Detailed summaries by category
- 🚀 **CLI Interface** - Interactive menu + quick commands
- 🐳 **Docker Ready** - Easy deployment

## 🚀 Quick Start

### Prerequisites
- Python 3.11+ 
- PostgreSQL database (local/external)
- Google Gemini AI API key

### 1. Setup
```bash
git clone <repository-url>
cd cashmate
pip install -r requirements.txt
cp .env.example .env
```

### 2. Configure Environment
```env
# Simple setup with DATABASE_URL
DATABASE_URL=postgresql://user:pass@host:port/database
GEMINI_API_KEY=your_gemini_api_key

# Or individual variables
POSTGRES_HOST=localhost
POSTGRES_DB=defaultdb  
POSTGRES_USER=username
POSTGRES_PASSWORD=password
```

### 3. Test Database Connection
```bash
# Test database connection and schema creation
python test_db.py
```

### 4. Run CashMate
```bash
# Telegram Bot (Recommended)
python telegram_bot.py

# CLI mode
python main.py

# Docker
docker-compose up -d
```

## 📖 Usage Examples

### 🤖 Telegram Bot (Recommended)
```
User: /start
Bot: Welcome! Send transactions like: bakso 15k cash

User: bakso 15k pake cash
Bot: ✅ Expense recorded: Rp 15,000, Cash, Food

User: /summary
Bot: 📊 Monthly Summary: Income +Rp 0, Expenses -Rp 15,000

User: /recent
Bot: 📄 Recent transactions with details
```

### 💻 CLI Interface
```bash
CashMate> /input bakso 15k pake cash
→ Expense: Rp 15,000, Cash, Food

CashMate> /summary
→ Monthly report with categories
```

### 🚀 Quick Commands (Both Interfaces)
```bash
# Telegram & CLI
/input <transaction>  # Add transaction
/summary             # Monthly summary
/recent              # Recent transactions
/help               # Show menu
/start              # Bot welcome (Telegram only)
/balance            # Show account balances
/test               # Test connections
```

## 🗄️ Database Setup Guide

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

### Local Development
```bash
# CLI + PostgreSQL + Adminer
docker-compose --profile local up -d

# Telegram Bot + PostgreSQL + Adminer
docker-compose --profile telegram up -d
```

### External Database
```bash
# CLI with external database
docker-compose --profile external up -d

# Telegram Bot with external database
docker-compose --profile telegram-external up -d
```

### Production
```bash
# Build image
docker build -t cashmate .

# Run CLI mode
docker run -it --env-file .env cashmate python main.py

# Run Telegram Bot mode
docker run -d --env-file .env cashmate python telegram_bot.py
```

### Docker Profiles
- `local`: CLI + Local PostgreSQL
- `telegram`: Telegram Bot + Local PostgreSQL
- `external`: CLI + External Database
- `telegram-external`: Telegram Bot + External Database

## 🤖 AI Transaction Examples

The Gemini AI understands Indonesian natural language:

| Input | Parsed Output |
|-------|---------------|
| `bakso 15k pake cash` | Expense: Rp 15,000, Cash, Food |
| `gojek ke kantor 20rb` | Expense: Rp 20,000, Cash, Transport |
| `gaji bulan ini 5jt ke bank` | Income: Rp 5,000,000, Bank, Salary |
| `beli buku 50rb dana` | Expense: Rp 50,000, Dana, Shopping |

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
# Test database connection and schema creation
python test_db.py

# Test AI parser
python main.py "5"

# Check user schemas (replace USER_ID with actual Telegram user ID)
psql "connection_string" -c "\dt user_123.*"
```

### Common Fixes
- **Database connection failed**: Check credentials in `.env`
- **Schema not found**: Run `init.sql` on your database
- **AI parser errors**: Verify `GEMINI_API_KEY` and internet connection
- **Permission denied**: Grant schema permissions to user

## 📁 Project Structure

```
cashmate/
├── main.py              # CLI application entry point
├── db.py                # Database operations (schema: cashmate)
├── ai_parser.py         # Gemini AI transaction parsing  
├── init.sql             # Database schema initialization
├── requirements.txt     # Python dependencies
├── .env.example         # Configuration template
├── Dockerfile           # Container configuration
├── docker-compose.yml   # Docker setup with profiles
└── README.md           # This documentation
```

## 🛠️ Development

### Adding Features
1. **New categories**: Modify AI prompt in `ai_parser.py`
2. **Database changes**: Update `init.sql` and `db.py`  
3. **New commands**: Extend `handle_command()` in `main.py`

### API Usage
```python
from db import get_db
from ai_parser import get_parser

# Parse transaction
parser = get_parser()
data = parser.parse_transaction("bakso 15k cash")

# Save to database  
db = get_db()
transaction_id = db.insert_transaksi(data)

# Get summary
summary = db.get_monthly_summary(2024, 1)
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