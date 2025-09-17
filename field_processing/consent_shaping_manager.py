"""
Consent Shaping Manager

Handles the detection and proper formatting of consent form elements according to
Modento Forms schema requirements.
"""

import re
from typing import List, Dict, Any


class ConsentShapingManager:
    """Manages consent form specific processing and shaping"""
    
    # Patterns that indicate consent paragraph content
    CONSENT_PATTERNS = [
        r'.*I understand.*',
        r'.*I acknowledge.*',
        r'.*I agree.*',
        r'.*I consent.*',
        r'.*I authorize.*',
        r'.*I have been.*informed.*',
        r'.*risks.*benefits.*',
        r'.*alternative.*treatment.*',
        r'.*financial.*responsibility.*',
        r'.*informed.*consent.*',
    ]
    
    def __init__(self):
        """Initialize the consent shaping manager"""
        self.compiled_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.CONSENT_PATTERNS]
    
    def apply_consent_shaping(self, spec: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Detect consent paragraphs and shape them properly
        
        Args:
            spec: List of field dictionaries
            
        Returns:
            List of field dictionaries with properly shaped consent elements
        """
        # Look for consent-related text fields and ensure proper formatting
        for field in spec:
            if field.get('type') == 'text':
                control = field.get('control', {})
                html_text = control.get('html_text', '')
                
                if self._is_consent_content(html_text):
                    # Apply consent-specific formatting
                    field = self._format_consent_field(field)
        
        # Ensure proper consent form structure
        spec = self._ensure_consent_structure(spec)
        
        return spec
    
    def _is_consent_content(self, text: str) -> bool:
        """Check if text content represents consent information"""
        if not text:
            return False
        
        # Check against consent patterns
        for pattern in self.compiled_patterns:
            if pattern.search(text):
                return True
        
        # Additional checks for consent keywords
        consent_keywords = [
            'consent', 'acknowledge', 'understand', 'agree', 'authorize',
            'risks', 'benefits', 'complications', 'treatment', 'procedure'
        ]
        
        text_lower = text.lower()
        keyword_count = sum(1 for keyword in consent_keywords if keyword in text_lower)
        
        # If multiple consent keywords are present, likely consent content
        return keyword_count >= 2
    
    def _format_consent_field(self, field: Dict[str, Any]) -> Dict[str, Any]:
        """Format a consent field according to standards"""
        control = field.get('control', {})
        
        # Ensure proper HTML formatting
        for text_key in ['html_text', 'temporary_html_text']:
            if text_key in control:
                text = control[text_key]
                # Ensure text is wrapped in paragraph tags
                if text and not text.strip().startswith('<p>'):
                    control[text_key] = f"<p>{text.strip()}</p>"
        
        return field
    
    def _ensure_consent_structure(self, spec: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Ensure proper consent form structure with required elements"""
        # Check if this appears to be a consent form
        if not self._is_consent_form(spec):
            return spec
        
        # Ensure signature elements are present for consent forms
        spec = self._ensure_consent_signature_elements(spec)
        
        return spec
    
    def _is_consent_form(self, spec: List[Dict[str, Any]]) -> bool:
        """Determine if this specification represents a consent form"""
        # Look for consent indicators
        consent_indicators = 0
        
        for field in spec:
            # Check field titles and text content
            title = field.get('title', '').lower()
            section = field.get('section', '').lower()
            
            if any(word in title or word in section for word in ['consent', 'agreement', 'authorization']):
                consent_indicators += 1
            
            # Check text field content
            if field.get('type') == 'text':
                control = field.get('control', {})
                html_text = control.get('html_text', '').lower()
                if any(word in html_text for word in ['consent', 'understand', 'acknowledge', 'agree']):
                    consent_indicators += 1
        
        # If we have multiple consent indicators, likely a consent form
        return consent_indicators >= 2
    
    def _ensure_consent_signature_elements(self, spec: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Ensure consent forms have proper signature elements"""
        has_signature = any(field.get('type') == 'signature' for field in spec)
        has_date = any(field.get('key') == 'date_signed' for field in spec)
        
        if not has_signature:
            # Add signature field
            signature_field = {
                "key": "signature",
                "type": "signature",
                "title": "Signature",
                "section": "Signature",
                "optional": False,
                "control": {}
            }
            spec.append(signature_field)
        
        if not has_date:
            # Add date signed field
            date_field = {
                "key": "date_signed",
                "type": "date",
                "title": "Date Signed",
                "section": "Signature",
                "optional": False,
                "control": {"input_type": "past"}
            }
            spec.append(date_field)
        
        return spec
    
    def detect_consent_sections(self, text_lines: List[str]) -> Dict[str, Any]:
        """
        Detect consent form sections from text lines
        
        Args:
            text_lines: List of text lines from the document
            
        Returns:
            Dictionary with section information
        """
        sections = {
            'consent_paragraphs': [],
            'signature_section': False,
            'patient_info_section': False,
            'procedure_section': False
        }
        
        for i, line in enumerate(text_lines):
            line_lower = line.lower().strip()
            
            # Detect consent paragraphs
            if self._is_consent_content(line):
                sections['consent_paragraphs'].append({
                    'line_idx': i,
                    'content': line.strip()
                })
            
            # Detect signature section
            if any(word in line_lower for word in ['signature', 'sign', 'date signed']):
                sections['signature_section'] = True
            
            # Detect patient information section
            if any(word in line_lower for word in ['patient name', 'name:', 'patient info']):
                sections['patient_info_section'] = True
            
            # Detect procedure section
            if any(word in line_lower for word in ['procedure', 'treatment', 'surgery']):
                sections['procedure_section'] = True
        
        return sections
    
    def format_consent_text(self, text: str) -> str:
        """Format consent text for proper display"""
        if not text:
            return text
        
        # Clean up common formatting issues in consent text
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Ensure proper sentence spacing
        text = re.sub(r'\.(\w)', r'. \1', text)
        
        # Fix common punctuation issues
        text = re.sub(r'\s+([,.;:!?])', r'\1', text)
        
        return text