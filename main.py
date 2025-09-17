"""
CashMate Main Application
Personal money tracker with AI-powered transaction parsing.
"""

import os
import sys
import logging
from datetime import datetime, date
from typing import Dict, Any, Optional
import argparse
from dotenv import load_dotenv

# Import our modules
from db import get_db
from ai_parser import get_parser
from utils import (
    format_currency, format_summary_display, get_current_month,
    clean_transaction_input, validate_month
)

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class CashMateApp:
    """
    Main CashMate application class.
    """
    
    def __init__(self):
        self.db = get_db()
        self.parser = get_parser()
        self.running = True
        
        # Test connections on startup
        self._test_connections()
    
    def _test_connections(self):
        """Test database and AI connections."""
        logger.info("Testing connections...")
        
        # Test database
        if not self.db.test_connection():
            logger.error("Database connection failed!")
            sys.exit(1)
        
        # Test AI parser
        if not self.parser.test_parser():
            logger.warning("AI parser test failed, but continuing...")
        
        logger.info("Connections tested successfully")
    
    def process_transaction_input(self, user_input: str) -> bool:
        """Process transaction input from user."""
        try:
            cleaned_input = clean_transaction_input(user_input)
            if not cleaned_input:
                print("❌ Error: Empty transaction input")
                return False
            
            print(f"🤖 Processing: '{cleaned_input}'")
            
            # Parse with AI and save to database
            parsed_data = self.parser.parse_transaction(cleaned_input)
            self._display_parsed_data(parsed_data)
            
            transaction_id = self.db.insert_transaksi(parsed_data)
            print(f"✅ Transaction saved! (ID: {transaction_id})")
            return True
            
        except Exception as e:
            print(f"❌ Error processing transaction: {e}")
            return False
    
    def _display_parsed_data(self, data: Dict[str, Any]):
        """Display parsed transaction data."""
        print(f"📊 Parsed data:")
        print(f"   Type: {data['tipe']}")
        print(f"   Amount: {format_currency(data['nominal'])}")
        print(f"   Account: {data['akun']}")
        print(f"   Category: {data['kategori']}")
        print(f"   Notes: {data['catatan']}")
    
    def show_monthly_summary(self, year: Optional[int] = None, month: Optional[int] = None):
        """Show monthly summary."""
        try:
            if year is None or month is None:
                year, month = get_current_month()
            
            summary = self.db.get_monthly_summary(year, month)
            print(format_summary_display(summary))
            
        except Exception as e:
            print(f"❌ Error showing summary: {e}")
    
    def show_recent_transactions(self, limit: int = 10):
        """Show recent transactions."""
        try:
            print(f"\n📄 Recent Transactions (Last {limit})")
            print("=" * 60)
            
            transactions = self.db.get_recent_transactions(limit)
            if not transactions:
                print("No transactions found.")
                return
            
            for i, trans in enumerate(transactions, 1):
                timestamp = trans['waktu'].strftime('%Y-%m-%d %H:%M')
                display = format_transaction_display(trans)
                print(f"{i:2d}. [{timestamp}] {display}")
            
        except Exception as e:
            print(f"❌ Error showing transactions: {e}")
    
    def show_menu(self):
        """Display the main menu."""
        print("\n🏦 CashMate - Personal Money Tracker")
        print("=" * 40)
        print("1. Add Transaction (e.g., 'bakso 15k pake cash')")
        print("2. View Monthly Summary")
        print("3. View Recent Transactions")
        print("4. View Custom Summary")
        print("5. Test AI Parser")
        print("6. Test Database Connection")
        print("0. Exit")
        print("\n💡 Quick Commands:")
        print("   /input <transaction> - Add transaction directly")
        print("   /summary - Current month summary")
        print("   /recent - Recent transactions")
        print("   /help - Show this menu")
        print("   /quit - Exit application")
    
    def handle_command(self, command: str) -> bool:
        """Handle command input."""
        command = command.strip()
        if not command:
            return True
        
        # Quick commands
        if self._handle_quick_commands(command):
            return command not in ['/quit', '/exit']
        
        # Menu options
        if command.isdigit():
            return self._handle_menu_options(command)
        
        # Transaction text
        return self._handle_transaction_text(command)
    
    def _handle_quick_commands(self, command: str) -> bool:
        """Handle slash commands."""
        commands = {
            '/summary': self.show_monthly_summary,
            '/recent': self.show_recent_transactions,
            '/help': self.show_menu,
        }
        
        if command.startswith('/input '):
            self.process_transaction_input(command)
            return True
        
        if command in commands:
            commands[command]()
            return True
        
        if command in ['/quit', '/exit']:
            print("👋 Goodbye!")
            return True
        
        return False
    
    def _handle_menu_options(self, command: str) -> bool:
        """Handle numbered menu options."""
        actions = {
            '1': self._menu_add_transaction,
            '2': self.show_monthly_summary,
            '3': self.show_recent_transactions,
            '4': self._menu_custom_summary,
            '5': self._test_ai_parser,
            '6': self._test_database,
            '0': lambda: (print("👋 Goodbye!"), False)[1]
        }
        
        if command in actions:
            result = actions[command]()
            return result if result is not None else True
        return True
    
    def _menu_add_transaction(self):
        """Menu option 1: Add transaction."""
        print("\n💰 Add Transaction")
        print("Enter details (e.g., 'bakso 15k pake cash'):")
        trans_input = input(">> ").strip()
        if trans_input:
            self.process_transaction_input(trans_input)
    
    def _menu_custom_summary(self):
        """Menu option 4: Custom summary."""
        print("\n📊 Custom Summary")
        try:
            year = int(input("Enter year (YYYY): ").strip())
            month = int(input("Enter month (1-12): ").strip())
            if validate_month(month):
                self.show_monthly_summary(year, month)
            else:
                print("❌ Invalid month. Please enter 1-12.")
        except ValueError:
            print("❌ Invalid input. Please enter numeric values.")
    
    def _test_ai_parser(self):
        """Menu option 5: Test AI parser."""
        print("\n🤖 Testing AI Parser...")
        result = "✅ AI Parser test completed!" if self.parser.test_parser() else "❌ AI Parser test failed!"
        print(result)
    
    def _test_database(self):
        """Menu option 6: Test database."""
        print("\n🗄️ Testing Database Connection...")
        result = "✅ Database connection successful!" if self.db.test_connection() else "❌ Database connection failed!"
        print(result)
    
    def _handle_transaction_text(self, command: str) -> bool:
        """Handle plain text as transaction."""
        if len(command) > 3 and not command.startswith('/'):
            print(f"🤔 Interpreting as transaction: '{command}'")
            self.process_transaction_input(command)
        else:
            print(f"❌ Unknown command: {command}")
            print("Type '/help' to see available commands.")
        return True
    
    def run_interactive(self):
        """Run the interactive CLI interface."""
        print("🚀 Starting CashMate Interactive Mode")
        self.show_menu()
        
        while self.running:
            try:
                user_input = input("\nCashMate> ").strip()
                if not self.handle_command(user_input):
                    break
            except KeyboardInterrupt:
                print("\n\n👋 Goodbye!")
                break
            except EOFError:
                print("\n\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"❌ Unexpected error: {e}")
                logger.error(f"Interactive mode error: {e}")
    
    def run_single_command(self, command: str):
        """
        Run a single command and exit.
        
        Args:
            command (str): Command to execute
        """
        print(f"🚀 Executing command: {command}")
        self.handle_command(command)

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="CashMate - Personal Money Tracker with AI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                           # Interactive mode
  python main.py "/input bakso 15k cash"   # Add transaction
  python main.py "/summary"                # Show monthly summary
  python main.py "/recent"                 # Show recent transactions
        """
    )
    
    parser.add_argument(
        'command',
        nargs='?',
        help='Command to execute (optional, starts interactive mode if not provided)'
    )
    
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug logging'
    )
    
    args = parser.parse_args()
    
    # Configure logging level
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        # Initialize app
        app = CashMateApp()
        
        # Run command or interactive mode
        if args.command:
            app.run_single_command(args.command)
        else:
            app.run_interactive()
            
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        logger.error(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()