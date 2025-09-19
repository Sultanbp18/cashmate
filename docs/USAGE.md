# CashMate Usage Guide

## Getting Started

### First Time Setup

1. Start a chat with your CashMate bot on Telegram
2. Send `/start` command
3. The bot will automatically create your personal database schema
4. You're ready to track expenses!

### Basic Usage

CashMate uses natural language processing to understand your transactions. Simply send messages like:

```
gaji 5jt ke bca
bakso 15k
bensin 50rb dana
transfer bca ke gopay 100k
```

## Transaction Types

### Income (Pemasukan)

```
gaji 5jt ke bca
bonus 1jt dana
freelance 500k cash
```

### Expenses (Pengeluaran)

```
makan 25k
bensin 50rb
belanja shopee 200k
gojek 15k
```

### Transfers (Transfer)

```
transfer bca ke dana 100k
dari cash ke gopay 50k
tarik tunai bca 200k
topup gopay 30k
```

## Commands

### Core Commands

| Command | Description | Example |
|---------|-------------|---------|
| `/start` | Initialize bot and setup database | `/start` |
| `/help` | Show help and usage guide | `/help` |
| `/accounts` | View all accounts and balances | `/accounts` |
| `/summary` | Monthly financial summary | `/summary` |
| `/recent` | Last 10 transactions | `/recent` |
| `/test` | Test system connections | `/test` |

### Account Management

#### Viewing Accounts

Send `/accounts` to see:
- All your accounts (cash, bank, e-wallet)
- Current balances
- Account types

#### Automatic Account Creation

Accounts are created automatically when you first use them:

```
# First transaction creates 'cash' account
bakso 15k

# First transaction creates 'bca' account
gaji 5jt ke bca

# First transaction creates 'dana' account
topup dana 50k
```

### Transaction Management

#### Adding Transactions

Use natural language:

```
# Food expenses
bakso 15k
kopi starbucks 25k
makan siang 30k

# Transportation
gojek 20k
bensin 50rb
parkir 5k

# Shopping
baju 150k
belanja indomaret 75k
shopee 200k
```

#### Transfer Transactions

```
# Between bank accounts
transfer bca ke mandiri 500k

# Withdraw cash
tarik tunai bca 200k
ambil dari bni 100k

# Top up e-wallet
topup gopay 50k
isi saldo dana 30k

# Move money between accounts
dari cash ke dana 100k
```

## Amount Formats

CashMate understands various amount formats:

| Format | Example | Parsed As |
|--------|---------|-----------|
| `k` | `15k` | 15,000 |
| `rb` | `50rb` | 50,000 |
| `jt` | `2jt` | 2,000,000 |
| Plain | `15000` | 15,000 |

## Categories

### Automatic Categorization

CashMate automatically categorizes transactions:

#### Food & Dining
- `bakso`, `nasi`, `ayam`, `kopi`, `jus`, `restoran`
- `warung`, `cafe`, `food court`

#### Transportation
- `gojek`, `grab`, `taxi`, `bensin`, `tol`
- `parkir`, `terminal`, `stasiun`

#### Shopping
- `beli`, `belanja`, `shopee`, `tokopedia`
- `mall`, `supermarket`, `minimarket`

#### Entertainment
- `nonton`, `bioskop`, `game`, `musik`
- `travel`, `hotel`, `wisata`

#### Other
- Everything else goes to `lainnya`

### Custom Categories

For transactions that don't fit standard categories:

```
proyek freelance 750k ke bca  # Goes to 'gaji'
hadiah ulang tahun 100k       # Goes to 'lainnya'
```

## Reports & Analytics

### Monthly Summary

Send `/summary` to get:

- 💰 Total Income
- 💸 Total Expenses
- 📈 Net Balance
- 📊 Transaction Count
- 📋 Breakdown by Category
- 💳 Account Balances

### Recent Transactions

Send `/recent` to see your last 10 transactions with:
- Date and time
- Transaction type (+ for income, - for expenses)
- Amount
- Account used
- Category
- Notes

### Account Overview

Send `/accounts` to see:
- All your accounts grouped by type
- Current balance for each account
- Total balance across all accounts

## Advanced Features

### Multi-Account Support

Track money across different accounts:

```
# Bank accounts
gaji 5jt ke bca
bonus 2jt ke mandiri

# E-wallets
topup gopay 100k
belanja shopee 50k dana

# Cash
makan 25k cash
gojek 15k
```

### Transfer Tracking

Monitor money movement between accounts:

```
# Transfer between banks
transfer bca ke mandiri 1jt

# Cash withdrawals
tarik tunai bca 500k

# E-wallet topups
topup dana 200k dari bca
```

### Balance Protection

CashMate prevents overspending:

```
# This will succeed
belanja 50k cash  # If cash balance >= 50,000

# This will fail with clear error
belanja 100k cash  # If cash balance < 100,000
```

## Tips & Best Practices

### 1. Be Specific

```
✅ Good: "bakso pak boss 15k"
✅ Good: "bensin pom bensin 50rb"
❌ Bad: "makan 25k"
```

### 2. Use Account Names

```
✅ Good: "gaji 5jt ke bca"
✅ Good: "belanja 100k dana"
❌ Bad: "gaji 5jt"  # Uses default 'cash'
```

### 3. Regular Check-ins

- Send `/summary` weekly to track spending
- Send `/accounts` to monitor balances
- Send `/recent` to review recent transactions

### 4. Consistent Naming

```
✅ Good: Use consistent account names
gaji ke bca
transfer bca ke dana

❌ Bad: Mix different names for same account
gaji ke bca
transfer bank central asia ke dana
```

### 5. Category Awareness

CashMate learns from your transaction patterns:

```
# Initially might categorize as 'lainnya'
proyek website 1jt

# After similar transactions, learns 'gaji'
freelance 750k
proyek mobile app 2jt
```

## Troubleshooting

### Transaction Not Recognized

If your message isn't recognized as a transaction:

```
🤔 *Pesan tidak dikenali sebagai transaksi*

Pesan Anda: `halo bot`

💡 *Untuk mencatat transaksi, gunakan:*
• `/input bakso 15k cash`
• Atau kirim pesan seperti: `bakso 15k`, `gaji 5jt`, `bensin 50rb`
```

**Solution**: Include amount indicators (`k`, `rb`, `jt`) or transaction keywords

### Insufficient Balance

```
❌ *Transaksi Gagal - Saldo Tidak Cukup*

Input: `belanja 100k cash`
Error: Saldo tidak cukup di akun cash. Saldo tersedia: Rp 50,000, Dibutuhkan: Rp 100,000

💡 *Solusi:*
• Cek saldo akun dengan `/accounts`
• Pastikan saldo mencukupi sebelum transaksi
• Atau gunakan akun lain yang memiliki saldo cukup
```

**Solution**: Check balances with `/accounts` or use different account

### AI Processing Issues

If AI parser fails, CashMate falls back to rule-based parsing:

```
❌ *Gagal Memproses Transaksi*

Input: `makan ayam goreng 25k`
Error: AI parsing failed

💡 *Saran:*
• Coba format sederhana: `bakso 15k cash`
• Atau tunggu sebentar jika sistem sibuk
```

**Solution**: Use simpler transaction formats

### Multiple Bot Instances

```
❌ MULTIPLE BOT INSTANCES DETECTED!

This usually means:
1. Another bot instance is already running
2. Previous bot instance wasn't properly stopped
```

**Solution**: Stop other bot processes and restart

## Examples

### Daily Usage

```
User: /start
Bot: ✅ Database Anda sudah siap!

User: gaji bulan ini 5jt ke bca
Bot: 💰 Transaksi Berhasil Dicatat!

User: bakso 15k
Bot: 💸 Transaksi Berhasil Dicatat!

User: /accounts
Bot: 💳 Akun & Saldo Anda...

User: /summary
Bot: 📊 Ringkasan bulan ini...
```

### Transfer Example

```
User: transfer bca ke dana 100k
Bot: 🔄 Transfer Berhasil!

User: /accounts
Bot: 💳 Akun & Saldo Anda:
     🏦 BCA: Rp 4,900,000
     📱 Dana: Rp 100,000
```

### Error Handling

```
User: belanja 1jt cash
Bot: ❌ Transaksi Gagal - Saldo Tidak Cukup

User: /accounts
Bot: 💳 Akun & Saldo Anda:
     💵 Cash: Rp 50,000

User: transfer bca ke cash 200k
Bot: 🔄 Transfer Berhasil!

User: belanja 150k cash
Bot: 💸 Transaksi Berhasil Dicatat!
```

## Getting Help

- Send `/help` for usage guide
- Send `/test` to check system status
- Include transaction keywords and amounts
- Use consistent account names
- Check balances regularly with `/accounts`