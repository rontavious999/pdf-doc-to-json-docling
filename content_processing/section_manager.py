"""
Section Manager Module

Handles section detection and field categorization across forms.
"""

import re
from typing import List, Dict, Any


class SectionManager:
    """Manage section detection and field categorization"""
    
    def __init__(self):
        self.section_patterns = {
            'patient_info': re.compile(r'patient\s*information', re.IGNORECASE),
            'contact': re.compile(r'contact\s*information', re.IGNORECASE),
            'insurance': re.compile(r'insurance|dental\s*plan', re.IGNORECASE),
            'medical_history': re.compile(r'medical\s*history|health\s*history', re.IGNORECASE),
            'consent': re.compile(r'consent|terms|agreement', re.IGNORECASE),
            'signature': re.compile(r'signature', re.IGNORECASE),
        }
    
    def detect_section(self, text: str, context_lines: List[str], current_section: str = "Patient Information Form") -> str:
        """Detect form section based on content and context with improved section tracking"""
        # Check current line and surrounding context
        all_text = ' '.join([text] + context_lines[:10])
        
        # More specific section detection for dental forms
        text_lower = text.lower()
        context_lower = ' '.join(context_lines[:10]).lower()
        
        # If the current context mentions a specific section override, use it
        section_indicators = {
            "FOR CHILDREN/MINORS ONLY": ["for children/minors only", "minor", "children", "responsible party"],
            "Primary Dental Plan": ["primary dental plan", "dental benefit plan information primary", "primary dental"],
            "Secondary Dental Plan": ["secondary dental plan"],
            "Signature": ["patient responsibilities", "payment", "dental benefit plans", "scheduling", "authorization", "signature", "initial", "agree"]
        }
        
        # Check for explicit section indicators in context
        for section_name, indicators in section_indicators.items():
            if any(indicator in context_lower for indicator in indicators):
                # Additional checks for disambiguation
                if section_name == "Primary Dental Plan":
                    if 'secondary' not in context_lower:
                        return section_name
                elif section_name == "Secondary Dental Plan":
                    if 'secondary' in context_lower:
                        return section_name
                else:
                    return section_name
        
        # Insurance/dental plan related fields - improved detection
        if any(keyword in text_lower for keyword in ['insurance', 'dental plan', 'group number', 'id number', 'plan/group', 'name of insured', 'patient relationship to insured']):
            if 'secondary' in context_lower or 'second' in context_lower:
                return "Secondary Dental Plan"
            else:
                return "Primary Dental Plan"
        
        # Medical history related
        if any(keyword in text_lower for keyword in ['medical', 'health', 'history', 'condition', 'medication', 'allerg', 'surgery']):
            return "Medical History"
        
        # Emergency contact - but only if not in children section
        if any(keyword in text_lower for keyword in ['emergency', 'notify']) and 'minor' not in context_lower:
            return "Patient Information Form"  # Emergency contact is part of main patient info
        
        # Children/minors section - improved detection
        if any(keyword in text_lower for keyword in ['minor', 'children', 'parent', 'guardian', 'custody', 'school', 'responsible party']):
            return "FOR CHILDREN/MINORS ONLY"
        
        # Signature and consent - improved detection with more precise matching
        if (any(keyword in text_lower for keyword in ['signature', 'consent', 'terms', 'agree', 'responsibilities', 'payment', 'scheduling']) or 
            (re.search(r'\binitial\b', text_lower) and not re.search(r'\b(middle|mi)\s+initial\b', text_lower))):
            return "Signature"
        
        # Basic patient info fields
        if any(keyword in text_lower for keyword in ['first name', 'last name', 'nickname', 'date of birth', 'birthdate', 'sex', 'marital', 'ssn', 'social security']):
            return "Patient Information Form"
        
        # Address and contact fields - but check context for which section
        if any(keyword in text_lower for keyword in ['street', 'city', 'state', 'zip', 'address', 'phone', 'mobile', 'home', 'work', 'e-mail', 'email']):
            # Check context to determine which section's address/contact info
            if 'minor' in context_lower or 'children' in context_lower or 'responsible party' in context_lower:
                return "FOR CHILDREN/MINORS ONLY"
            elif 'insurance' in context_lower or 'dental plan' in context_lower:
                if 'secondary' in context_lower:
                    return "Secondary Dental Plan"
                else:
                    return "Primary Dental Plan"
            elif 'work address' in context_lower:
                return "Patient Information Form"  # Work address is part of patient info
            else:
                return "Patient Information Form"
        
        # Employment information
        if any(keyword in text_lower for keyword in ['employed', 'employer', 'occupation']):
            if 'different from above' in context_lower or 'minor' in context_lower:
                return "FOR CHILDREN/MINORS ONLY"
            else:
                return "Patient Information Form"
        
        # Default to current section or Patient Information Form
        return current_section if current_section else "Patient Information Form"
    
    def detect_section_headers_universal(self, text_lines: List[str]) -> Dict[int, str]:
        """Detect section headers in the text"""
        sections = {}
        
        for i, line in enumerate(text_lines):
            line_clean = line.strip()
            if not line_clean:
                continue
            
            line_lower = line_clean.lower()
            
            # Look for markdown headers (starting with ##)
            if line_clean.startswith('##'):
                header_text = line_clean.replace('#', '').strip()
                sections[i] = header_text
                continue
            
            # Look for specific section patterns
            section_patterns = {
                "Patient Information Form": [
                    "patient information", "patient info", "new patient", "patient demographics"
                ],
                "FOR CHILDREN/MINORS ONLY": [
                    "for children/minors only", "minors only", "children only", "responsible party"
                ],
                "Primary Dental Plan": [
                    "primary dental plan", "dental benefit plan information", "insurance information"
                ],
                "Secondary Dental Plan": [
                    "secondary dental plan", "additional insurance"
                ],
                "Signature": [
                    "patient responsibilities", "authorization", "signature", "financial agreement"
                ]
            }
            
            for section_name, patterns in section_patterns.items():
                if any(pattern in line_lower for pattern in patterns):
                    sections[i] = section_name
                    break
            
            # Look for standalone section headers (short lines that end with colon or are in caps)
            if (len(line_clean) < 50 and 
                (line_clean.endswith(':') or line_clean.isupper()) and
                len(line_clean.split()) <= 5):
                sections[i] = line_clean.rstrip(':')
        
        return sections
    
    def get_current_section_universal(self, line_idx: int, sections: Dict[int, str], default: str = "Patient Information Form") -> str:
        """Get the current section for a given line index"""
        current_section = default
        
        # Find the most recent section header before this line
        for section_line_idx in sorted(sections.keys()):
            if section_line_idx <= line_idx:
                current_section = sections[section_line_idx]
            else:
                break
        
        return current_section