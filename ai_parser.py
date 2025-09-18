"""
CashMate AI Parser Module
Handles transaction parsing using Google's Gemini AI API.
"""

import os
import json
import logging
from typing import Dict, Any, Optional
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GeminiTransactionParser:
    """
    Transaction parser using Google's Gemini AI to extract structured data from natural language input.
    """
    
    def __init__(self):
        self.api_key = os.getenv('GEMINI_API_KEY')
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables")
        
        # Configure Gemini AI
        genai.configure(api_key=self.api_key)
        # Use the correct model name
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        
        logger.info("Gemini AI parser initialized successfully")
    
    def create_parsing_prompt(self, user_input: str) -> str:
        """
        Create a detailed prompt for Gemini AI to parse transaction data.
        Load prompt template from external file.
        
        Args:
            user_input (str): Raw user input
        
        Returns:
            str: Formatted prompt for AI
        """
        try:
            prompt_file = os.path.join(os.path.dirname(__file__), 'config', 'transaction_prompt.txt')
            with open(prompt_file, 'r', encoding='utf-8') as f:
                prompt_template = f.read()
            return prompt_template.format(user_input=user_input)
        except FileNotFoundError:
            logger.warning("Prompt file not found, using fallback prompt")
            return self._fallback_prompt(user_input)
    
    def _fallback_prompt(self, user_input: str) -> str:
        """Fallback prompt if external file is not available."""
        return f'''
Analyze this transaction: "{user_input}"

Return only JSON with: tipe, nominal, akun, kategori, catatan
Rules: k=1000, rb=1000, jt=1000000. Default akun="cash", tipe="pengeluaran"

Example: "bakso 15k" → {{"tipe": "pengeluaran", "nominal": 15000, "akun": "cash", "kategori": "makanan", "catatan": "bakso"}}
'''
    
    def parse_transaction(self, user_input: str) -> Dict[str, Any]:
        """
        Parse natural language transaction input using Gemini AI with fallback.

        Args:
            user_input (str): Natural language transaction description

        Returns:
            dict: Structured transaction data
        """
        try:
            # Clean input
            cleaned_input = user_input.strip()
            if cleaned_input.startswith('/input '):
                cleaned_input = cleaned_input[7:]  # Remove '/input ' prefix

            if not cleaned_input:
                raise ValueError("Empty transaction input")

            # Try AI parsing first
            try:
                return self._parse_with_ai(cleaned_input)
            except Exception as ai_error:
                logger.warning(f"AI parsing failed: {ai_error}, trying fallback parser")
                try:
                    return self._parse_with_fallback(cleaned_input)
                except Exception as fallback_error:
                    logger.error(f"Both AI and fallback parsing failed. AI: {ai_error}, Fallback: {fallback_error}")
                    raise ValueError(f"Unable to parse transaction. Please try a simpler format like 'bakso 15k cash'")

        except Exception as e:
            logger.error(f"Transaction parsing error: {e}")
            raise ValueError(f"Failed to parse transaction: {e}")

    def _parse_with_ai(self, user_input: str) -> Dict[str, Any]:
        """Parse using Gemini AI."""
        # Create prompt
        prompt = self.create_parsing_prompt(user_input)

        # Generate response using Gemini
        logger.info(f"Parsing transaction with AI: '{user_input}'")
        response = self.model.generate_content(prompt)

        if not response.text:
            raise ValueError("Empty response from Gemini AI")

        # Clean and parse JSON response
        json_text = response.text.strip()

        # Remove markdown code blocks if present
        if json_text.startswith('```json'):
            json_text = json_text[7:]
        if json_text.startswith('```'):
            json_text = json_text[3:]
        if json_text.endswith('```'):
            json_text = json_text[:-3]

        json_text = json_text.strip()

        # Parse JSON
        parsed_data = json.loads(json_text)

        # Validate required fields based on transaction type
        tipe = parsed_data.get('tipe', '').lower()

        if tipe == 'transfer':
            required_fields = ['tipe', 'nominal', 'akun_asal', 'akun_tujuan', 'catatan']
        else:
            required_fields = ['tipe', 'nominal', 'akun', 'kategori', 'catatan']

        for field in required_fields:
            if field not in parsed_data:
                raise ValueError(f"Missing required field: {field}")

        # Validate and clean data
        validated_data = self._validate_transaction_data(parsed_data)

        logger.info(f"AI successfully parsed transaction: {validated_data}")
        return validated_data

    def _parse_with_fallback(self, user_input: str) -> Dict[str, Any]:
        """Fallback parser for simple transaction patterns."""
        logger.info(f"Using fallback parser for: '{user_input}'")

        # Simple pattern matching for common cases
        input_lower = user_input.lower()

        # Default values
        result = {
            'tipe': 'pengeluaran',
            'nominal': 0,
            'akun': 'cash',
            'kategori': 'lainnya',
            'catatan': user_input
        }

        # Detect transfer keywords first
        transfer_keywords = ['transfer', 'pindah', 'tarik tunai', 'tarik', 'ambil', 'kirim', 'dari', 'ke']
        if any(keyword in input_lower for keyword in transfer_keywords):
            result['tipe'] = 'transfer'
            result['kategori'] = 'transfer'
            logger.info(f"Fallback: Detected transfer from keywords: {[kw for kw in transfer_keywords if kw in input_lower]}")

            # Try to extract source and destination accounts for transfers
            words = input_lower.split()
            # Look for patterns like "dari X ke Y" or "X ke Y"
            dari_index = -1
            ke_index = -1

            for i, word in enumerate(words):
                if word == 'dari':
                    dari_index = i
                elif word == 'ke':
                    ke_index = i

            # Initialize with defaults
            source_account = 'cash'
            dest_account = 'cash'

            if dari_index != -1 and ke_index != -1 and ke_index > dari_index:
                # Pattern: "dari source ke destination"
                if dari_index + 1 < len(words):
                    source_account = self._detect_account_from_word(words[dari_index + 1])
                if ke_index + 1 < len(words):
                    dest_account = self._detect_account_from_word(words[ke_index + 1])
            elif ke_index != -1:
                # Pattern: "source ke destination"
                if ke_index > 0:
                    source_account = self._detect_account_from_word(words[ke_index - 1])
                if ke_index + 1 < len(words):
                    dest_account = self._detect_account_from_word(words[ke_index + 1])

            result['akun_asal'] = source_account
            result['akun_tujuan'] = dest_account
            logger.info(f"Fallback: Transfer detected - from '{source_account}' to '{dest_account}'")

        # Detect income keywords
        income_keywords = ['gaji', 'salary', 'bonus', 'terima', 'dapat', 'penghasilan', 'pendapatan', 'insentif']
        if any(keyword in input_lower for keyword in income_keywords):
            result['tipe'] = 'pemasukan'
            result['kategori'] = 'gaji'
            logger.info(f"Fallback: Detected income from keywords: {[kw for kw in income_keywords if kw in input_lower]}")

        # Extract amount
        import re
        # Find patterns like: 50k, 500rb, 2jt, 50000
        amount_patterns = [
            r'(\d+(?:\.\d+)?)\s*jt',  # 2jt -> 2000000
            r'(\d+(?:\.\d+)?)\s*rb',  # 500rb -> 500000
            r'(\d+(?:\.\d+)?)\s*k',   # 50k -> 50000
            r'(\d+(?:\.\d+)?)'        # 50000 -> 50000
        ]

        for pattern in amount_patterns:
            match = re.search(pattern, input_lower)
            if match:
                amount = float(match.group(1))
                if 'jt' in input_lower:
                    amount *= 1000000
                elif 'rb' in input_lower:
                    amount *= 1000
                elif 'k' in input_lower:
                    amount *= 1000

                result['nominal'] = amount
                break

        # Detect account based on transaction type
        if result['tipe'] == 'transfer':
            # For transfers, we already set akun_asal and akun_tujuan above
            # But we might need to improve the account detection for transfers
            pass
        else:
            # For regular transactions, detect single account
            # First check for specific bank names
            specific_banks = ['bca', 'bri', 'bni', 'mandiri', 'btn', 'cimb', 'danamon', 'mega', 'permata', 'panin', 'bukopin', 'maybank']
            for bank in specific_banks:
                if bank in input_lower:
                    result['akun'] = bank  # Use the specific bank name
                    logger.info(f"Fallback: Detected specific bank '{bank}' from input")
                    break
            else:
                # If no specific bank found, check other account types
                account_keywords = {
                    'cash': ['cash', 'tunai'],
                    'bank': ['bank', 'rekening'],  # Generic bank
                    'dana': ['dana'],
                    'gopay': ['gopay'],
                    'ovo': ['ovo'],
                    'kartu kredit': ['kartu kredit', 'credit card', 'cc', 'visa', 'mastercard']
                }

                for account, keywords in account_keywords.items():
                    if any(keyword in input_lower for keyword in keywords):
                        result['akun'] = account
                        logger.info(f"Fallback: Detected account '{account}' from keywords: {[kw for kw in keywords if kw in input_lower]}")
                        break

        # Validate result
        if result['nominal'] <= 0:
            raise ValueError("Could not extract valid amount from input")

        logger.info(f"Fallback parser result: {result}")
        return self._validate_transaction_data(result)
    
    def _validate_transaction_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and clean transaction data.

        Args:
            data (dict): Raw parsed data

        Returns:
            dict: Validated and cleaned data
        """
        validated = {}

        # Validate tipe
        tipe = str(data.get('tipe', '')).lower()
        if tipe not in ['pemasukan', 'pengeluaran', 'transfer']:
            tipe = 'pengeluaran'  # Default to expense
        validated['tipe'] = tipe

        # Validate nominal
        try:
            nominal = float(data.get('nominal', 0))
            if nominal <= 0:
                raise ValueError("Nominal must be positive")
            validated['nominal'] = nominal
        except (ValueError, TypeError):
            raise ValueError("Invalid nominal amount")

        # Handle transfer vs regular transactions
        if tipe == 'transfer':
            # Validate source account
            akun_asal = str(data.get('akun_asal', 'cash')).strip()
            if not akun_asal:
                akun_asal = 'cash'
            validated['akun_asal'] = akun_asal

            # Validate destination account
            akun_tujuan = str(data.get('akun_tujuan', 'cash')).strip()
            if not akun_tujuan:
                akun_tujuan = 'cash'
            validated['akun_tujuan'] = akun_tujuan

            # For transfers, we don't need kategori
            validated['kategori'] = 'transfer'
        else:
            # Regular transaction validation
            # Validate akun
            akun = str(data.get('akun', 'cash')).strip()
            if not akun:
                akun = 'cash'
            validated['akun'] = akun

            # Validate kategori
            kategori = str(data.get('kategori', 'lainnya')).strip()
            if not kategori:
                kategori = 'lainnya'
            validated['kategori'] = kategori

        # Validate catatan
        catatan = str(data.get('catatan', '')).strip()
        if not catatan:
            catatan = 'Transaksi'
        validated['catatan'] = catatan

        return validated

    def _detect_account_from_word(self, word: str) -> str:
        """Detect account type from a single word."""
        word_lower = word.lower()

        # Specific bank detection
        specific_banks = ['bca', 'bri', 'bni', 'mandiri', 'btn', 'cimb', 'danamon', 'mega', 'permata', 'panin', 'bukopin', 'maybank']
        if word_lower in specific_banks:
            return word_lower

        # Other account types
        account_mapping = {
            'cash': ['cash', 'tunai', 'uang'],
            'dana': ['dana'],
            'gopay': ['gopay'],
            'ovo': ['ovo'],
            'bank': ['bank', 'rekening']
        }

        for account, keywords in account_mapping.items():
            if word_lower in keywords:
                return account

        # Default to the word itself (might be a custom account name)
        return word_lower

    def parse_multiple_transactions(self, user_inputs: list) -> list:
        """
        Parse multiple transaction inputs.
        
        Args:
            user_inputs (list): List of transaction input strings
        
        Returns:
            list: List of parsed transaction dictionaries
        """
        results = []
        for i, input_text in enumerate(user_inputs):
            try:
                parsed = self.parse_transaction(input_text)
                results.append(parsed)
            except Exception as e:
                logger.error(f"Error parsing transaction {i+1}: {e}")
                results.append({
                    'error': str(e),
                    'input': input_text
                })
        return results
    
    def test_parser(self) -> bool:
        """
        Test the parser with sample inputs.
        
        Returns:
            bool: True if test passes
        """
        test_cases = [
            "bakso 15k pake cash",
            "gojek ke kantor 20rb",
            "gaji bulan ini 5jt ke bank",
            "beli buku 50rb pake dana",
            "makan siang 25k"
        ]
        
        try:
            for test_input in test_cases:
                result = self.parse_transaction(test_input)
                logger.info(f"Test '{test_input}' -> {result}")
            
            logger.info("Parser test completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Parser test failed: {e}")
            return False

# Global parser instance
transaction_parser = GeminiTransactionParser()

def parse_transaction_input(user_input: str) -> Dict[str, Any]:
    """
    Parse transaction input using the global parser instance.
    
    Args:
        user_input (str): Natural language transaction description
    
    Returns:
        dict: Structured transaction data
    """
    return transaction_parser.parse_transaction(user_input)

def get_parser():
    """
    Get the global transaction parser instance.
    
    Returns:
        GeminiTransactionParser: Parser instance
    """
    return transaction_parser