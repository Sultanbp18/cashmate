# CashMate Setup Guide

## Prerequisites

- Python 3.11 or higher
- PostgreSQL database (local or cloud)
- Google Gemini AI API key
- Telegram Bot Token

## Quick Setup

### 1. Clone and Install

```bash
git clone <repository-url>
cd cashmate
pip install -r requirements.txt
```

### 2. Environment Configuration

Copy the example environment file:

```bash
cp .env.example .env
```

Edit `.env` with your configuration:

```env
# Database Configuration (choose one option)
DATABASE_URL=postgresql://user:pass@host:port/database
# OR
POSTGRES_HOST=localhost
POSTGRES_DB=cashmate
POSTGRES_USER=your_username
POSTGRES_PASSWORD=your_password

# AI Configuration
GEMINI_API_KEY=your_gemini_api_key_here

# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here

# Application Configuration
DEBUG=false
```

### 3. Database Setup

#### Option A: Using Docker (Recommended for development)

```bash
# Start PostgreSQL container
docker run --name cashmate-db -e POSTGRES_DB=cashmate -e POSTGRES_USER=cashmate -e POSTGRES_PASSWORD=password -p 5432:5432 -d postgres:15

# Or using docker-compose
docker-compose up -d
```

#### Option B: Local PostgreSQL

```bash
# Create database
createdb cashmate

# Or using psql
psql -c "CREATE DATABASE cashmate;"
```

#### Option C: Cloud Database

CashMate works with any PostgreSQL provider:

- **Aiven**: `postgresql://user:pass@host.aivencloud.com:port/defaultdb?sslmode=require`
- **AWS RDS**: `postgresql://user:pass@rds-endpoint:5432/postgres`
- **Railway**: `postgresql://postgres:pass@containers.railway.app:port/railway`
- **Heroku**: `postgres://user:pass@host:5432/database`

### 4. Getting API Keys

#### Google Gemini AI API

1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create a new API key
3. Add to `.env` as `GEMINI_API_KEY`

#### Telegram Bot Token

1. Message [@BotFather](https://t.me/botfather) on Telegram
2. Send `/newbot` and follow instructions
3. Copy the token to `.env` as `TELEGRAM_BOT_TOKEN`

### 5. Run CashMate

```bash
# Using the new structure
python main.py

# Or directly
python -m src.bot.main
```

## Advanced Configuration

### Database Schema

CashMate uses a multi-tenant schema approach where each user gets their own schema:

```
Database: [your_database]
├── Schema: user_123456789 (auto-created per user)
│   ├── Table: akun (accounts)
│   └── Table: transaksi (transactions)
```

### Environment Variables Reference

| Variable | Description | Example |
|----------|-------------|---------|
| `DATABASE_URL` | Complete PostgreSQL connection string | `postgresql://user:pass@host:port/db` |
| `POSTGRES_HOST` | Database host | `localhost` |
| `POSTGRES_PORT` | Database port | `5432` |
| `POSTGRES_DB` | Database name | `cashmate` |
| `POSTGRES_USER` | Database user | `cashmate` |
| `POSTGRES_PASSWORD` | Database password | `password` |
| `GEMINI_API_KEY` | Google Gemini API key | `AIza...` |
| `TELEGRAM_BOT_TOKEN` | Telegram bot token | `123456:ABC...` |
| `DEBUG` | Enable debug logging | `false` |

### Docker Deployment

#### Build Image

```bash
docker build -t cashmate .
```

#### Run Container

```bash
# With environment file
docker run --env-file .env -d --name cashmate-bot cashmate

# Or with individual variables
docker run -e DATABASE_URL="..." -e GEMINI_API_KEY="..." -e TELEGRAM_BOT_TOKEN="..." -d cashmate
```

#### Docker Compose

```yaml
version: '3.8'
services:
  cashmate:
    build: .
    env_file: .env
    depends_on:
      - db

  db:
    image: postgres:15
    environment:
      POSTGRES_DB: cashmate
      POSTGRES_USER: cashmate
      POSTGRES_PASSWORD: password
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

## Troubleshooting

### Database Connection Issues

```bash
# Test database connection
python -c "from src.core.database import get_db; db = get_db(); print('Connected' if db.test_connection() else 'Failed')"

# Check PostgreSQL service
sudo systemctl status postgresql

# Test with psql
psql "your_connection_string" -c "SELECT version();"
```

### AI Parser Issues

```bash
# Test AI parser
python -c "from src.services.nlp_processor import get_parser; p = get_parser(); print('AI OK' if p.test_parser() else 'AI Failed')"
```

### Telegram Bot Issues

```bash
# Check bot token
curl "https://api.telegram.org/bot<YOUR_TOKEN>/getMe"

# Test bot commands
python main.py
# Then send /test to your bot on Telegram
```

### Common Errors

1. **"Multiple bot instances"**: Stop other bot processes first
   ```bash
   pkill -f "python.*main.py"
   ```

2. **"Schema does not exist"**: Schemas are created automatically on first user interaction

3. **"AI API quota exceeded"**: Check your Gemini API usage limits

4. **"Database permission denied"**: Grant proper permissions to database user

## Development Setup

### Install Development Dependencies

```bash
pip install -r requirements-dev.txt
```

### Run Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific tests
pytest tests/test_nlp_processor.py
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

### Development Workflow

1. Create feature branch: `git checkout -b feature/new-feature`
2. Make changes and test
3. Format code: `black src/ && isort src/`
4. Run tests: `pytest`
5. Commit changes: `git commit -m "Add new feature"`
6. Push branch: `git push origin feature/new-feature`
7. Create Pull Request

## Production Deployment

### Using Docker (Recommended)

```bash
# Build optimized image
docker build --no-cache -t cashmate:latest .

# Run in production
docker run -d --name cashmate-prod --restart unless-stopped --env-file .env cashmate:latest
```

### Using Systemd

Create `/etc/systemd/system/cashmate.service`:

```ini
[Unit]
Description=CashMate Telegram Bot
After=network.target

[Service]
Type=simple
User=cashmate
WorkingDirectory=/path/to/cashmate
ExecStart=/path/to/venv/bin/python main.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Then:

```bash
sudo systemctl daemon-reload
sudo systemctl enable cashmate
sudo systemctl start cashmate
```

### Monitoring

```bash
# Check service status
sudo systemctl status cashmate

# View logs
sudo journalctl -u cashmate -f

# Docker logs
docker logs -f cashmate-prod