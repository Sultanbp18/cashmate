#!/usr/bin/env python3
"""
CashMate Parser Test Script
Test AI parser functionality locally without Telegram bot.
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import our modules
from ai_parser import get_parser

def test_parser():
    """Test the AI parser with various inputs."""
    print("🤖 CashMate AI Parser Test")
    print("=" * 50)

    # Initialize parser
    try:
        parser = get_parser()
        print("✅ Parser initialized successfully")
    except Exception as e:
        print(f"❌ Parser initialization failed: {e}")
        return

    # Test cases
    test_cases = [
        "gaji 50k cash",
        "bakso 15k",
        "beli buku 25rb dana",
        "gojek 20rb",
        "bonus 1jt bank",
        "makan siang 30k",
        "bensin 50rb gopay",
        "terima uang 100k",
        "bayar listrik 75rb",
        "salary 5jt"
    ]

    print(f"\n🧪 Testing {len(test_cases)} cases...\n")

    for i, test_input in enumerate(test_cases, 1):
        print(f"{i:2d}. Testing: '{test_input}'")
        print("-" * 40)

        try:
            result = parser.parse_transaction(test_input)

            # Display result
            tipe_emoji = "💰" if result['tipe'] == 'pemasukan' else "💸"
            print(f"   {tipe_emoji} Tipe: {result['tipe']}")
            print(f"   💵 Nominal: Rp {result['nominal']:,.0f}")
            print(f"   🏦 Akun: {result['akun']}")
            print(f"   📂 Kategori: {result['kategori']}")
            print(f"   📝 Catatan: {result['catatan']}")
            print("   ✅ SUCCESS")

        except Exception as e:
            print(f"   ❌ ERROR: {e}")

        print()

def test_fallback():
    """Test fallback parser specifically."""
    print("🔄 Testing Fallback Parser")
    print("=" * 30)

    parser = get_parser()

    # Force fallback by temporarily disabling AI
    original_model = parser.model
    parser.model = None  # This will force fallback

    test_cases = [
        "gaji 50k cash",
        "bakso 15k",
        "beli buku 25rb dana"
    ]

    for test_input in test_cases:
        print(f"Testing: '{test_input}'")
        try:
            result = parser.parse_transaction(test_input)
            print(f"   ✅ {result['tipe']} - Rp {result['nominal']:,.0f} - {result['akun']}")
        except Exception as e:
            print(f"   ❌ {e}")
        print()

    # Restore original model
    parser.model = original_model

def main():
    """Main function."""
    if len(sys.argv) > 1:
        # Test specific input
        test_input = ' '.join(sys.argv[1:])
        print(f"Testing specific input: '{test_input}'")

        try:
            parser = get_parser()
            result = parser.parse_transaction(test_input)

            print("✅ Result:")
            print(f"   Tipe: {result['tipe']}")
            print(f"   Nominal: Rp {result['nominal']:,.0f}")
            print(f"   Akun: {result['akun']}")
            print(f"   Kategori: {result['kategori']}")
            print(f"   Catatan: {result['catatan']}")

        except Exception as e:
            print(f"❌ Error: {e}")

    else:
        # Run full test suite
        test_parser()
        print("\n" + "="*50)
        test_fallback()

if __name__ == "__main__":
    main()