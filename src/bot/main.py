"""
Main entry point for CashMate Telegram bot.
"""

import os
import logging
import asyncio
from telegram import Update, BotCommand
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv

from .handlers import (
    start_command, handle_transaction_message,
    summary_command, recent_command, accounts_command,
    help_command, test_command
)
from .keyboards import get_main_menu_commands

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class CashMateTelegramBot:
    """
    Simplified Telegram Bot interface for CashMate application.
    """

    def __init__(self):
        self.token = os.getenv('TELEGRAM_BOT_TOKEN')
        if not self.token:
            raise ValueError("TELEGRAM_BOT_TOKEN not found in environment variables")

        # Initialize bot application
        self.application = Application.builder().token(self.token).build()
        self._setup_handlers()

        logger.info("CashMate Telegram Bot initialized")

    def _setup_handlers(self):
        """Setup all command and message handlers."""

        # Core command handlers
        self.application.add_handler(CommandHandler("start", start_command))
        self.application.add_handler(CommandHandler("help", help_command))
        self.application.add_handler(CommandHandler("accounts", accounts_command))
        self.application.add_handler(CommandHandler("summary", summary_command))
        self.application.add_handler(CommandHandler("recent", recent_command))
        self.application.add_handler(CommandHandler("test", test_command))

        # Message handler for natural language input
        self.application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_transaction_message)
        )

    async def setup_bot_commands(self):
        """Setup simplified bot commands menu."""
        commands = get_main_menu_commands()
        await self.application.bot.set_my_commands(commands)

    async def run(self):
        """Run the bot."""
        try:
            # Setup bot commands
            await self.setup_bot_commands()

            # Start bot
            logger.info("Starting CashMate Telegram Bot...")
            await self.application.initialize()
            await self.application.start()
            await self.application.updater.start_polling()

            logger.info("CashMate Telegram Bot is running!")

            # Keep running
            stop_signal = asyncio.Event()

            def signal_handler():
                stop_signal.set()

            # Handle shutdown signals
            try:
                import signal
                signal.signal(signal.SIGINT, signal_handler)
                signal.signal(signal.SIGTERM, signal_handler)
            except (OSError, ValueError):
                pass

            await stop_signal.wait()

        except Exception as e:
            error_message = str(e)
            if "Conflict: terminated by other getUpdates request" in error_message:
                logger.error("❌ MULTIPLE BOT INSTANCES DETECTED!")
                logger.error("This usually means:")
                logger.error("1. Another bot instance is already running")
                logger.error("2. Previous bot instance wasn't properly stopped")
                logger.error("3. Multiple containers/processes running the same bot")
                logger.error("")
                logger.error("SOLUTION:")
                logger.error("1. Stop all other bot instances first")
                logger.error("2. Kill any existing Python processes: pkill -f main.py")
                logger.error("3. If using Docker: docker stop <container_id>")
                logger.error("4. Wait 30 seconds, then restart the bot")
                logger.error("")
                logger.error("To check running processes: ps aux | grep main.py")
                raise ValueError("Multiple bot instances detected. Please stop other instances first.")
            else:
                logger.error(f"Bot startup error: {e}")
                raise
        finally:
            logger.info("Stopping CashMate Telegram Bot...")
            try:
                await self.application.stop()
                await self.application.shutdown()
            except Exception as e:
                logger.error(f"Error during shutdown: {e}")

def main():
    """Main entry point for Telegram Bot."""
    try:
        # Initialize and run bot
        bot = CashMateTelegramBot()
        asyncio.run(bot.run())

    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal bot error: {e}")

if __name__ == "__main__":
    main()