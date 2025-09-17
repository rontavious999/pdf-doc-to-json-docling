"""
Field Detector Module

Handles core field pattern recognition and checkbox/bullet detection.
"""

import re
from typing import List, Dict, Any, Optional, Tuple, Pattern


class FieldDetector:
    """Core field detection patterns and utilities"""
    
    # Centralized regex patterns for maintainability - RECOMMENDATION 3: Unified bullet detection
    CHECKBOX_SYMBOLS = r"[□■☐☑✅◉●○•\-\–\*\[\]\(\)]"
    CHECKBOX_CHAR_CLASS = r"□■☐☑✅◉●○•\-\–\*\[\]\(\)"
    
    # Enhanced bullet patterns for risk sections and consent forms
    BULLET_PATTERNS = {
        'standard_bullets': r'[•\-\–\*]',
        'checkbox_bullets': r'[□■☐☑✅]',
        'circle_bullets': r'[◉●○]',
        'numbered_bullets': r'\d+[\.\)]\s*',
        'lettered_bullets': r'[a-zA-Z][\.\)]\s*',
        'unicode_bullets': r'[\u2022\u2023\u2043\u204C\u204D\u2219\u25A0\u25A1\u25CF\u25CB]'
    }
    
    def __init__(self):
        self.field_patterns = {
            # Common field patterns in dental forms
            'name': re.compile(r'(?:first\s*name|last\s*name|patient\s*name|full\s*name)(?:\s*[:_]|\s*$)', re.IGNORECASE),
            'email': re.compile(r'e-?mail(?:\s*[:_]|\s*$)', re.IGNORECASE),
            'phone': re.compile(r'(?:phone|mobile|home|work)(?:\s*[:_]|\s*$)', re.IGNORECASE),
            'date': re.compile(r'(?:date|birth|dob)(?:\s*[:_]|\s*$)', re.IGNORECASE),
            'address': re.compile(r'(?:address|street|city|state|zip)(?:\s*[:_]|\s*$)', re.IGNORECASE),
            'ssn': re.compile(r'(?:ssn|social\s*security)(?:\s*[:_]|\s*$)', re.IGNORECASE),
            'signature': re.compile(r'signature(?:\s*[:_]|\s*$)', re.IGNORECASE),
        }
        
        # RECOMMENDATION 2: Consent-specific field patterns for better extraction 
        self.consent_field_patterns = {
            'printed_name': re.compile(r'(?:printed?\s*name|print\s*name|name\s*\(print\)|patient\s*print)', re.IGNORECASE),
            'date_of_birth': re.compile(r'(?:date\s*of\s*birth|birth\s*date|dob|born)', re.IGNORECASE),
            'relationship': re.compile(r'(?:relationship|relation\s*to|guardian|parent|spouse)', re.IGNORECASE),
            'consent_date': re.compile(r'(?:consent\s*date|date\s*of\s*consent|today)', re.IGNORECASE),
        }
    
    def get_unified_bullet_pattern(self) -> Pattern:
        """RECOMMENDATION 3: Get unified pattern for all bullet types"""
        all_patterns = '|'.join(self.BULLET_PATTERNS.values())
        return re.compile(f'^\\s*(?:{all_patterns})\\s*(.+)', re.MULTILINE)
    
    def has_checkbox_symbol(self, text: str) -> bool:
        """Check if text contains any checkbox symbol"""
        return bool(re.search(self.CHECKBOX_SYMBOLS, text))
    
    def get_checkbox_options_pattern(self):
        """Get regex pattern for extracting checkbox options"""
        return re.compile(rf"{self.CHECKBOX_SYMBOLS}\s*([A-Za-z0-9][A-Za-z0-9\s\-/&\(\)']{{1,80}})(?=\s*{self.CHECKBOX_SYMBOLS}|\s*$)")
    
    def detect_field_type(self, text: str) -> str:
        """Detect field type based on text content with enhanced consent form support"""
        text_lower = text.lower()
        text_clean = text_lower.strip()
        
        # Enhanced signature field detection
        if any(keyword in text_clean for keyword in [
            'signature:', 'sign:', 'signed:', 'patient signature', 'signature of', 'x____'
        ]):
            return "signature"
        
        # Enhanced date field detection - now includes "today"
        if any(keyword in text_clean for keyword in [
            'date', 'birth', 'dob', 'today', 'signed date', 'consent date'
        ]):
            return "date"
        
        # Initials detection - specific for initial fields
        if (('initial' in text_clean or 'initials' in text_clean) and 
            not any(exclusion in text_clean for exclusion in ['middle initial', 'mi', 'middle'])):
            return "input"  # Per reference, initials are input fields with input_type: "initials"
        
        # Enhanced radio detection for better question recognition
        radio_indicators = ['yes/no', 'male/female', 'check one', 'circle one', 'select one', 'married/single']
        if any(indicator in text_clean for indicator in radio_indicators):
            return "radio"
        
        # Enhanced checkbox detection for options and lists
        checkbox_indicators = ['check all', 'select all', 'list of', 'following:', 'options:']
        if (self.has_checkbox_symbol(text) or 
            any(indicator in text_clean for indicator in checkbox_indicators)):
            return "checkbox"
        
        # Enhanced address/states detection
        if any(keyword in text_clean for keyword in ['state', 'states']):
            # Special handling for "State" fields - they should be "states" type
            if text_clean.strip() == 'state' or 'state:' in text_clean:
                return "states"
        
        # Input field detection with comprehensive patterns
        input_indicators = [
            'name', 'address', 'street', 'city', 'zip', 'phone', 'email', 'e-mail',
            'ssn', 'social security', 'occupation', 'employer', 'insurance', 'license',
            'id number', 'plan', 'group', 'relationship', 'emergency', 'nickname'
        ]
        if any(indicator in text_clean for indicator in input_indicators):
            return "input"
        
        # Text content detection for consent forms and descriptions
        # Look for longer descriptive text that should be display-only
        if (len(text) > 100 or 
            any(keyword in text_clean for keyword in [
                'patient responsibilities', 'payment terms', 'dental benefit', 
                'scheduling', 'authorization', 'consent', 'understand', 'agree'
            ])):
            return "text"
        
        # Header detection for section titles
        if (text.endswith(':') and len(text) < 50 and 
            any(keyword in text_clean for keyword in [
                'information', 'plan', 'history', 'signature', 'responsibilities'
            ])):
            return "header"
        
        # Default to input for form fields that we can't specifically categorize
        if '_' in text or ':' in text:
            return "input"
        
        # Last resort - if it looks like form content but doesn't fit other categories
        return "text"
    
    def extract_checkbox_options(self, line: str) -> List[str]:
        """Extract checkbox options from a line using centralized checkbox pattern"""
        pattern = self.get_checkbox_options_pattern()
        matches = pattern.findall(line)
        
        # Clean up the extracted options
        cleaned_options = []
        for match in matches:
            option = match.strip()
            if len(option) > 0 and len(option) <= 80:  # Reasonable option length
                cleaned_options.append(option)
        
        return cleaned_options
    
    def collect_checkbox_run(self, lines: List[str], i: int) -> Tuple[List[Dict[str, Any]], int]:
        """Collect checkbox sequences starting from line i"""
        options = []
        current_idx = i
        
        # Look ahead to collect all checkbox options in sequence
        while current_idx < len(lines):
            line = lines[current_idx]
            if self.has_checkbox_symbol(line):
                # Extract options from this line
                line_options = self.extract_checkbox_options(line)
                for opt in line_options:
                    if opt:  # Only add non-empty options
                        options.append({
                            "name": opt,
                            "value": self._slugify(opt)
                        })
                current_idx += 1
            else:
                # Stop if no more checkbox symbols found
                break
        
        return options, current_idx - 1  # Return last processed line index
    
    def _slugify(self, text: str, fallback: str = "option") -> str:
        """Convert text to a valid option value"""
        if not text or not text.strip():
            return fallback
        
        # Remove special characters and spaces, convert to lowercase
        slug = re.sub(r'[^\w\s-]', '', text.lower())
        slug = re.sub(r'[-\s]+', '_', slug)
        return slug.strip('_') or fallback