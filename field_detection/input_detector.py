"""
Input Detector Module

Handles input field type classification and inline field parsing.
"""

import re
from typing import List, Tuple


class InputDetector:
    """Detect input field types and parse inline field patterns"""
    
    def __init__(self):
        self.field_patterns = {
            'name': re.compile(r'(?:first\s*name|last\s*name|patient\s*name|full\s*name)(?:\s*[:_]|\s*$)', re.IGNORECASE),
            'email': re.compile(r'e-?mail(?:\s*[:_]|\s*$)', re.IGNORECASE),
            'phone': re.compile(r'(?:phone|mobile|home|work)(?:\s*[:_]|\s*$)', re.IGNORECASE),
            'date': re.compile(r'(?:date|birth|dob)(?:\s*[:_]|\s*$)', re.IGNORECASE),
            'address': re.compile(r'(?:address|street|city|state|zip)(?:\s*[:_]|\s*$)', re.IGNORECASE),
            'ssn': re.compile(r'(?:ssn|social\s*security)(?:\s*[:_]|\s*$)', re.IGNORECASE),
            'signature': re.compile(r'signature(?:\s*[:_]|\s*$)', re.IGNORECASE),
        }
    
    def detect_input_type(self, text: str) -> str:
        """Detect specific input type for input fields"""
        text_lower = text.lower()
        
        # Email detection
        if self.field_patterns['email'].search(text) or 'e-mail' in text_lower:
            return 'email'
        
        # Phone detection  
        elif self.field_patterns['phone'].search(text) or any(word in text_lower for word in ['mobile', 'home phone', 'work phone', 'cell']):
            return 'phone'
        
        # SSN detection
        elif 'ssn' in text_lower or 'social security' in text_lower:
            return 'ssn'
        
        # Zip code detection
        elif 'zip' in text_lower:
            return 'zip'
        
        # Initials detection - be more specific
        elif ('initial' in text_lower or text_lower.strip() in ['mi', 'm.i.', 'middle initial', 'middle init']) and len(text) < 25:
            return 'initials'
        
        # Address detection for better field typing
        elif any(word in text_lower for word in ['street', 'address', 'apt', 'unit', 'suite']):
            return 'name'  # Keep as 'name' since Modento doesn't have 'address' input_type
        
        # Number detection - for IDs, license numbers, etc.
        elif (any(word in text_lower for word in ['number', 'id', '#']) 
              and 'license' not in text_lower 
              and 'phone' not in text_lower):
            return 'number'
        
        # Default to name for most other fields
        else:
            return 'name'
    
    def detect_input_field_universal(self, line: str) -> List[Tuple[str, str]]:
        """Detect input fields in a line"""
        fields = []
        
        # First check exact patterns for precise field naming
        exact_patterns = {
            # Main name line pattern - this is critical
            r'First\s*_{10,}.*?MI\s*_{2,}.*?Last\s*_{10,}.*?Nickname\s*_{5,}': [
                ('First Name', 'first_name'),
                ('Middle Initial', 'mi'), 
                ('Last Name', 'last_name'),
                ('Nickname', 'nickname')
            ],
            # Address line pattern
            r'Street\s*_{30,}.*?Apt/Unit/Suite\s*_{5,}': [
                ('Street', 'street'),
                ('Apt/Unit/Suite', 'apt_unit_suite')
            ],
            # City/State/Zip pattern
            r'City\s*_{20,}.*?State\s*_{5,}.*?Zip\s*_{10,}': [
                ('City', 'city'),
                ('State', 'state'),
                ('Zip', 'zip')
            ],
            # Main phone line pattern  
            r'Mobile\s*_{10,}.*?Home\s*_{10,}.*?Work\s*_{10,}': [
                ('Mobile', 'mobile'),
                ('Home', 'home'),
                ('Work', 'work')
            ],
            # E-mail and driver's license pattern
            r'E-Mail\s*_{20,}.*?Drivers License #': [
                ('E-Mail', 'e_mail'),
                ('Drivers License #', 'drivers_license')
            ],
        }
        
        # Check if line matches any exact pattern
        for pattern, field_mappings in exact_patterns.items():
            if re.search(pattern, line, re.IGNORECASE):
                # Use the exact field mappings instead of extracting from line
                for field_title, field_key in field_mappings:
                    fields.append((field_title, line))
                return fields  # Return early to avoid double extraction
        
        # Fallback to generic patterns if no exact match
        
        # Pattern 1: Enhanced "Label:" pattern
        if ':' in line and not line.strip().startswith('##'):
            # Handle multiple colons - take the part before first colon as potential field
            parts = line.split(':')
            if len(parts) >= 2:
                potential_field = parts[0].strip()
                
                # Filter out common non-field text
                non_field_indicators = [
                    'section', 'part', 'page', 'instructions', 'please', 'note',
                    'form', 'information', 'check', 'circle', 'complete'
                ]
                
                if (len(potential_field) > 2 and len(potential_field) < 50 and
                    not any(indicator in potential_field.lower() for indicator in non_field_indicators)):
                    fields.append((potential_field, line))
        
        # Pattern 2: Enhanced underscore patterns for fields
        underscore_pattern = r'([A-Za-z][A-Za-z\s/\-#\.]{2,40})\s*[_]{3,}'
        matches = re.finditer(underscore_pattern, line)
        
        for match in matches:
            field_name = match.group(1).strip()
            # Clean up field names
            if len(field_name) > 2 and not field_name.lower() in ['date', 'name', 'form']:
                fields.append((field_name, line))
        
        return fields
    
    def parse_inline_fields(self, line: str) -> List[Tuple[str, str]]:
        """Parse inline field patterns from a line"""
        fields = []
        
        # Use the universal detection as the primary method
        detected_fields = self.detect_input_field_universal(line)
        
        # Additional specific patterns for inline fields
        if not detected_fields:
            # Pattern for fields with underscores
            if '_' in line:
                # Try to extract field labels before underscores
                pattern = r'([A-Za-z][A-Za-z\s/\-#\.]{1,30})\s*[_]{2,}'
                matches = re.finditer(pattern, line)
                
                for match in matches:
                    field_name = match.group(1).strip()
                    if len(field_name) > 1:
                        fields.append((field_name, line))
        else:
            fields.extend(detected_fields)
        
        return fields