"""
Keyboards and menus for CashMate Telegram bot.
"""

from telegram import BotCommand

def get_main_menu_commands():
    """Get main menu commands for bot."""
    commands = [
        BotCommand("start", "Mulai menggunakan CashMate"),
        BotCommand("help", "Bantuan dan panduan"),
        BotCommand("accounts", "Lihat akun & saldo"),
        BotCommand("summary", "Ringkasan bulanan"),
        BotCommand("recent", "Transaksi terakhir"),
        BotCommand("test", "Test koneksi sistem"),
    ]
    return commands

# Note: Currently no inline keyboards are used in the bot
# This file is prepared for future keyboard implementations