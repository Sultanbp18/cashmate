#!/usr/bin/env python3
"""
CashMate - Personal Money Tracker
Main entry point for the application.
"""

import sys
import os

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.bot.main import main

if __name__ == "__main__":
    main()