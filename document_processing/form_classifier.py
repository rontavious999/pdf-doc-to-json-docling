"""
Form Classifier Module

Handles form type detection and classification.
"""

import re
from typing import List, Dict, Any


class FormClassifier:
    """Classify form types based on content analysis"""
    
    def __init__(self):
        # Form classification patterns
        self.form_classification_patterns = {
            'records_release': [
                re.compile(r'release\s*of\s*(?:patient\s*)?records', re.IGNORECASE),
                re.compile(r'(?:medical|dental|patient)\s*records?\s*release', re.IGNORECASE),
                re.compile(r'authorization\s*to\s*release', re.IGNORECASE),
                re.compile(r'consent\s*for\s*release', re.IGNORECASE),
                re.compile(r'section\s*a:\s*patient\s*information', re.IGNORECASE),
                re.compile(r'select\s*information\s*to\s*be\s*released', re.IGNORECASE),
            ],
            'structured_consent': [
                re.compile(r'informed\s*consent', re.IGNORECASE),
                re.compile(r'treatment\s*consent', re.IGNORECASE),
                re.compile(r'procedure\s*consent', re.IGNORECASE),
            ],
            'narrative_consent': [
                re.compile(r'risks?\s*and\s*benefits?', re.IGNORECASE),
                re.compile(r'complications', re.IGNORECASE),
                re.compile(r'side\s*effects?', re.IGNORECASE),
            ]
        }
    
    def detect_form_type(self, text_lines: List[str]) -> str:
        """Enhanced form type detection with classification"""
        # Join all text for comprehensive analysis
        full_text = ' '.join(text_lines).lower()
        
        # Count matches for each form type
        form_type_scores = {}
        
        for form_type, patterns in self.form_classification_patterns.items():
            score = 0
            for pattern in patterns:
                matches = len(pattern.findall(full_text))
                score += matches
            form_type_scores[form_type] = score
        
        # Specific form type detection logic
        
        # Patient Information Form detection (most common)
        patient_info_indicators = [
            'patient name', 'first name', 'last name', 'date of birth',
            'address', 'phone', 'insurance', 'dental plan', 'emergency contact'
        ]
        patient_info_score = sum(1 for indicator in patient_info_indicators if indicator in full_text)
        
        if patient_info_score >= 3:
            return "patient_info"
        
        # Records Release Form detection
        if form_type_scores['records_release'] > 0:
            # Additional checks for records release
            records_keywords = ['release', 'authorization', 'medical records', 'dental records']
            if sum(1 for keyword in records_keywords if keyword in full_text) >= 2:
                return "records_release"
        
        # Consent Form detection (structured)
        if form_type_scores['structured_consent'] > 0:
            consent_keywords = ['consent', 'procedure', 'treatment', 'risks', 'benefits']
            if sum(1 for keyword in consent_keywords if keyword in full_text) >= 2:
                return "structured_consent"
        
        # Consent Form detection (narrative/detailed)
        if form_type_scores['narrative_consent'] > 0:
            narrative_keywords = ['complications', 'side effects', 'risks and benefits']
            if sum(1 for keyword in narrative_keywords if keyword in full_text) >= 1:
                return "narrative_consent"
        
        # Enhanced specific form detection
        
        # NPF (New Patient Form) specific detection
        npf_indicators = [
            'preferred method of contact', 'marital status', 'employed by',
            'in case of emergency', 'is the patient a minor'
        ]
        npf_score = sum(1 for indicator in npf_indicators if indicator in full_text)
        
        if npf_score >= 2:
            return "patient_info"  # NPF is a type of patient info form
        
        # Biopsy consent detection
        if 'biopsy' in full_text and any(word in full_text for word in ['consent', 'procedure']):
            return "biopsy_consent"
        
        # Endodontic consent detection
        if any(word in full_text for word in ['endodontic', 'root canal']) and 'consent' in full_text:
            return "endodontic_consent"
        
        # Crown & Bridge consent detection
        if any(word in full_text for word in ['crown', 'bridge', 'prosthetic']) and 'consent' in full_text:
            return "crown_bridge_consent"
        
        # Composite restoration consent detection
        if any(word in full_text for word in ['composite', 'restoration', 'filling']) and 'consent' in full_text:
            return "composite_consent"
        
        # Implant consent detection
        if any(word in full_text for word in ['implant', 'implant supported']) and 'consent' in full_text:
            return "implant_consent"
        
        # Denture consent detection
        if any(word in full_text for word in ['denture', 'dentures', 'partial denture', 'complete denture']) and 'consent' in full_text:
            return "denture_consent"
        
        # Default fallback based on content length and structure
        if len(text_lines) > 100:
            # Likely a detailed consent form
            return "detailed_consent"
        elif len(text_lines) > 50:
            # Likely a structured form
            return "structured_form"
        else:
            # Likely a simple form
            return "simple_form"