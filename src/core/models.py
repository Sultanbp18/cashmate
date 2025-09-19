"""
Database models and schema definitions for CashMate.
"""

from typing import Dict, Any, List
from datetime import datetime

class Account:
    """
    Account model representing user accounts (cash, bank, e-wallet).
    """

    def __init__(self, id: int = None, nama: str = "", tipe: str = "kas",
                 saldo: float = 0.0, created_at: datetime = None, updated_at: datetime = None):
        self.id = id
        self.nama = nama
        self.tipe = tipe
        self.saldo = saldo
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Account':
        """Create Account instance from dictionary."""
        return cls(
            id=data.get('id'),
            nama=data.get('nama', ''),
            tipe=data.get('tipe', 'kas'),
            saldo=float(data.get('saldo', 0)),
            created_at=data.get('created_at'),
            updated_at=data.get('updated_at')
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert Account to dictionary."""
        return {
            'id': self.id,
            'nama': self.nama,
            'tipe': self.tipe,
            'saldo': self.saldo,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class Transaction:
    """
    Transaction model representing income/expense transactions.
    """

    def __init__(self, id: int = None, tipe: str = "", nominal: float = 0.0,
                 id_akun: int = None, kategori: str = "", catatan: str = "",
                 waktu: datetime = None):
        self.id = id
        self.tipe = tipe  # 'pemasukan' or 'pengeluaran'
        self.nominal = nominal
        self.id_akun = id_akun
        self.kategori = kategori
        self.catatan = catatan
        self.waktu = waktu or datetime.now()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Transaction':
        """Create Transaction instance from dictionary."""
        return cls(
            id=data.get('id'),
            tipe=data.get('tipe', ''),
            nominal=float(data.get('nominal', 0)),
            id_akun=data.get('id_akun'),
            kategori=data.get('kategori', ''),
            catatan=data.get('catatan', ''),
            waktu=data.get('waktu')
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert Transaction to dictionary."""
        return {
            'id': self.id,
            'tipe': self.tipe,
            'nominal': self.nominal,
            'id_akun': self.id_akun,
            'kategori': self.kategori,
            'catatan': self.catatan,
            'waktu': self.waktu.isoformat() if self.waktu else None
        }

class TransactionWithAccount(Transaction):
    """
    Transaction model with account information included.
    """

    def __init__(self, id: int = None, tipe: str = "", nominal: float = 0.0,
                 id_akun: int = None, kategori: str = "", catatan: str = "",
                 waktu: datetime = None, akun: str = ""):
        super().__init__(id, tipe, nominal, id_akun, kategori, catatan, waktu)
        self.akun = akun

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TransactionWithAccount':
        """Create TransactionWithAccount instance from dictionary."""
        return cls(
            id=data.get('id'),
            tipe=data.get('tipe', ''),
            nominal=float(data.get('nominal', 0)),
            id_akun=data.get('id_akun'),
            kategori=data.get('kategori', ''),
            catatan=data.get('catatan', ''),
            waktu=data.get('waktu'),
            akun=data.get('akun', '')
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert TransactionWithAccount to dictionary."""
        data = super().to_dict()
        data['akun'] = self.akun
        return data

# Schema definitions for database table creation
ACCOUNT_TABLE_SCHEMA = """
CREATE TABLE IF NOT EXISTS cashmate.akun (
    id SERIAL PRIMARY KEY,
    nama VARCHAR(100) NOT NULL UNIQUE,
    tipe VARCHAR(50) NOT NULL DEFAULT 'kas',
    saldo DECIMAL(15,2) NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
"""

TRANSACTION_TABLE_SCHEMA = """
CREATE TABLE IF NOT EXISTS cashmate.transaksi (
    id SERIAL PRIMARY KEY,
    tipe VARCHAR(20) NOT NULL CHECK (tipe IN ('pemasukan', 'pengeluaran')),
    nominal DECIMAL(15,2) NOT NULL CHECK (nominal > 0),
    id_akun INTEGER NOT NULL REFERENCES cashmate.akun(id),
    kategori VARCHAR(100) NOT NULL,
    catatan TEXT,
    waktu TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
"""

# Indexes for performance
ACCOUNT_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_cashmate_akun_nama ON cashmate.akun(nama)",
    "CREATE INDEX IF NOT EXISTS idx_cashmate_akun_tipe ON cashmate.akun(tipe)"
]

TRANSACTION_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_cashmate_transaksi_waktu ON cashmate.transaksi(waktu)",
    "CREATE INDEX IF NOT EXISTS idx_cashmate_transaksi_tipe ON cashmate.transaksi(tipe)",
    "CREATE INDEX IF NOT EXISTS idx_cashmate_transaksi_kategori ON cashmate.transaksi(kategori)",
    "CREATE INDEX IF NOT EXISTS idx_cashmate_transaksi_id_akun ON cashmate.transaksi(id_akun)"
]

# Default accounts to create for new users
DEFAULT_ACCOUNTS = [
    ('cash', 'kas'),
    ('bca', 'bank'),
    ('bni', 'bank'),
    ('dana', 'e-wallet'),
    ('gopay', 'e-wallet')
]