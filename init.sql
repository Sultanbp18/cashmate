-- CashMate Database Initialization Script
-- Creates the cashmate schema and required tables

-- Create database (uncomment if creating new database)
-- CREATE DATABASE cashmate;
-- \c cashmate;

-- Create user (uncomment if creating dedicated user)
-- CREATE USER cashmate WITH ENCRYPTED PASSWORD 'your_secure_password';
-- GRANT ALL PRIVILEGES ON DATABASE cashmate TO cashmate;

-- Create schema
CREATE SCHEMA IF NOT EXISTS cashmate;

-- Set search path
SET search_path TO cashmate;

-- Create akun (accounts) table
CREATE TABLE IF NOT EXISTS cashmate.akun (
    id SERIAL PRIMARY KEY,
    nama VARCHAR(100) NOT NULL UNIQUE,
    tipe VARCHAR(50) NOT NULL DEFAULT 'kas',
    saldo DECIMAL(15,2) NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create transaksi (transactions) table
CREATE TABLE IF NOT EXISTS cashmate.transaksi (
    id SERIAL PRIMARY KEY,
    tipe VARCHAR(20) NOT NULL CHECK (tipe IN ('pemasukan', 'pengeluaran')),
    nominal DECIMAL(15,2) NOT NULL CHECK (nominal > 0),
    id_akun INTEGER NOT NULL REFERENCES cashmate.akun(id),
    kategori VARCHAR(100) NOT NULL,
    catatan TEXT,
    waktu TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_transaksi_waktu ON cashmate.transaksi(waktu);
CREATE INDEX IF NOT EXISTS idx_transaksi_tipe ON cashmate.transaksi(tipe);
CREATE INDEX IF NOT EXISTS idx_transaksi_kategori ON cashmate.transaksi(kategori);
CREATE INDEX IF NOT EXISTS idx_transaksi_akun ON cashmate.transaksi(id_akun);
CREATE INDEX IF NOT EXISTS idx_akun_nama ON cashmate.akun(nama);

-- Insert some default accounts
INSERT INTO cashmate.akun (nama, tipe, saldo)
VALUES
    ('cash', 'kas', 0),
    ('bni', 'bank', 0),
    ('bri', 'bank', 0),
    ('bca', 'bank', 0),
    ('dana', 'e-wallet', 0),
    ('gopay', 'e-wallet', 0),
    ('ovo', 'e-wallet', 0)
ON CONFLICT (nama) DO NOTHING;

-- Create trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION cashmate.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply trigger to akun table
DROP TRIGGER IF EXISTS update_akun_updated_at ON cashmate.akun;
CREATE TRIGGER update_akun_updated_at
    BEFORE UPDATE ON cashmate.akun
    FOR EACH ROW
    EXECUTE FUNCTION cashmate.update_updated_at_column();

-- Grant permissions to cashmate user (adjust as needed)
GRANT USAGE ON SCHEMA cashmate TO PUBLIC;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA cashmate TO PUBLIC;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA cashmate TO PUBLIC;

-- If using dedicated user, grant specific permissions:
-- GRANT USAGE ON SCHEMA cashmate TO cashmate;
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA cashmate TO cashmate;
-- GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA cashmate TO cashmate;

-- Display success message
DO $$
BEGIN
    RAISE NOTICE 'CashMate database schema "cashmate" and tables created successfully!';
END $$;