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
        self.model = genai.GenerativeModel('gemini-pro')
        
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
                return self._parse_with_fallback(cleaned_input)

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

        # Validate required fields
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

        # Detect income keywords
        income_keywords = ['gaji', 'salary', 'bonus', 'terima', 'dapat', 'penghasilan']
        if any(keyword in input_lower for keyword in income_keywords):
            result['tipe'] = 'pemasukan'
            result['kategori'] = 'gaji'

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

        # Detect account
        account_keywords = {
            'cash': ['cash', 'tunai'],
            'bank': ['bank', 'rekening'],
            'dana': ['dana'],
            'gopay': ['gopay'],
            'ovo': ['ovo']
        }

        for account, keywords in account_keywords.items():
            if any(keyword in input_lower for keyword in account_keywords[account]):
                result['tipe'] = account
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
        if tipe not in ['pemasukan', 'pengeluaran']:
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