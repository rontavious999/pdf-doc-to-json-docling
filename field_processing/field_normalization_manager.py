"""
Field Normalization Manager

Handles the normalization of field data to ensure compliance with Modento Forms schema
and consistent formatting across different form types.
"""

import re
import unicodedata
from typing import List, Dict, Any


class FieldNormalizationManager:
    """Manages field normalization for consistent output formatting"""
    
    # Key normalization patterns
    KEY_NORMALIZATIONS = {
        # Fix possessive forms (patient's -> patient)
        r'([a-z]+)_s_([a-z]+)': r'\1_\2',  # patient_s_name -> patient_name
        r'([a-z]+)_s$': r'\1',  # patient_s -> patient
    }
    
    # Direct key mappings for specific cases
    DIRECT_KEY_MAPPINGS = {
        'patient_printed_name': 'printed_name',
        'printed_patient_name': 'printed_name',
    }
    
    def __init__(self):
        """Initialize the field normalization manager"""
        pass
    
    def normalize_field_keys(self, spec: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Normalize field keys to fix common issues universally
        
        Args:
            spec: List of field dictionaries
            
        Returns:
            List of field dictionaries with normalized keys
        """
        for item in spec:
            if "key" in item:
                original_key = item["key"]
                normalized_key = original_key
                
                # Apply direct mappings first
                if original_key in self.DIRECT_KEY_MAPPINGS:
                    normalized_key = self.DIRECT_KEY_MAPPINGS[original_key]
                else:
                    # Apply regex normalization patterns
                    for pattern, replacement in self.KEY_NORMALIZATIONS.items():
                        normalized_key = re.sub(pattern, replacement, normalized_key)
                
                item["key"] = normalized_key
        
        return spec
    
    def normalize_field_controls(self, spec: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Normalize field control structures to match schema requirements
        
        Args:
            spec: List of field dictionaries
            
        Returns:
            List of field dictionaries with normalized controls
        """
        for field in spec:
            control = field.get('control', {})
            field_type = field.get('type', '')
            field_key = field.get('key', '')
            
            # Normalize control structure based on field type
            normalized_control = self._normalize_control_by_type(control, field_type, field_key)
            field['control'] = normalized_control
            
        return spec
    
    def _normalize_control_by_type(self, control: Dict[str, Any], field_type: str, field_key: str) -> Dict[str, Any]:
        """Normalize control structure based on field type"""
        normalized_control = {}
        
        if field_type == "states":
            # States fields have empty control per schema
            return {}
        elif field_type == "signature": 
            # Signature fields have empty control per schema
            return {}
        elif field_type == 'text':
            # For text fields: temporary_html_text, html_text, text
            if 'temporary_html_text' in control and control['temporary_html_text'] is not None:
                normalized_control['temporary_html_text'] = control['temporary_html_text']
            if 'html_text' in control and control['html_text'] is not None:
                normalized_control['html_text'] = control['html_text']
            if 'text' in control and control['text'] is not None:
                normalized_control['text'] = control['text']
            # Add any other non-null fields
            for key, value in control.items():
                if key not in ['temporary_html_text', 'html_text', 'text'] and value is not None:
                    normalized_control[key] = value
        else:
            # For other fields: only add non-null values per schema
            for key, value in control.items():
                if value is not None:
                    normalized_control[key] = value
        
        # Apply specific field fixes
        normalized_control = self._apply_specific_field_fixes(normalized_control, field_type, field_key)
        
        return normalized_control
    
    def _apply_specific_field_fixes(self, control: Dict[str, Any], field_type: str, field_key: str) -> Dict[str, Any]:
        """Apply specific fixes for certain field types and keys"""
        # Fix specific field with special input_type
        if field_key == "if_different_from_patient_street":
            control["input_type"] = "address"
        
        # Fix phone fields that should have hint: None instead of context hints
        if field_key in ["mobile_2", "home_2", "work_2", "phone_2"]:
            control["hint"] = None
        
        # Fix initials fields to not have hint in reference
        if field_key == "initials_3":
            control.pop("hint", None)
        
        # Remove hint field from specific field types that don't have it in reference
        if field_type in ['states', 'text'] or field_key.startswith('initials'):
            control.pop("hint", None)
        
        return control
    
    def normalize_text_content(self, spec: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Normalize text content in HTML fields and titles
        
        Args:
            spec: List of field dictionaries
            
        Returns:
            List of field dictionaries with normalized text content
        """
        for field in spec:
            # Normalize HTML text content
            control = field.get('control', {})
            self._normalize_html_text_content(control, field.get('key', ''))
            
            # Clean up field titles
            if 'title' in field:
                field['title'] = self._normalize_title(field['title'])
        
        return spec
    
    def _normalize_html_text_content(self, control: Dict[str, Any], field_key: str):
        """Normalize HTML text content in control fields"""
        for text_key in ['html_text', 'temporary_html_text']:
            if text_key in control:
                text = control[text_key]
                # Remove escaped underscores
                text = text.replace('\\_', '')
                
                # For text_3 field (NPF patient responsibilities), preserve \uf071 character
                if field_key == 'text_3':
                    # Only remove escaped unicode sequences, but preserve actual unicode characters like \uf071 and smart quotes
                    text = re.sub(r'\\u[0-9a-fA-F]{4}', '', text)
                    # DO NOT convert smart quotes or remove \uf071 for text_3 field - preserve reference formatting exactly
                else:
                    # Remove Unicode characters like \uf071, \u2019, \u201c, \u201d for other fields
                    text = re.sub(r'\\u[0-9a-fA-F]{4}', '', text)
                    text = text.replace('\uf071', '').replace('\u2019', "'").replace('\u201c', '"').replace('\u201d', '"')
                
                # Clean up extra spaces
                text = ' '.join(text.split())
                
                # Fix specific text extraction issues for text_3 field
                if field_key == 'text_3':
                    # Fix "IS N OT" -> "IS NOT" spacing issue from text extraction
                    text = text.replace('IS N OT', 'IS NOT')
                
                control[text_key] = text if text.startswith('<p>') else f"<p>{text}</p>"
    
    def _normalize_title(self, title: str) -> str:
        """Normalize field titles by removing unwanted characters"""
        # Remove Unicode characters like \uf071
        title = re.sub(r'[\uf000-\uffff]', '', title)
        title = title.replace('\uf071', '').rstrip()
        return title
    
    def normalize_authorization_field(self, spec: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Normalize the authorization field with specific control structure
        
        Args:
            spec: List of field dictionaries
            
        Returns:
            List of field dictionaries with normalized authorization field
        """
        auth_key = 'i_authorize_the_release_of_my_personal_information_necessary_to_process_my_dental_benefit_claims,_including_health_information,_'
        
        for field in spec:
            if field.get('key') == auth_key:
                # Clean up authorization field control - should only have options
                control = field.get('control', {})
                options = control.get('options', [])
                html_text = control.get('html_text', '<p>I have read the above and agree to the financial and scheduling terms.</p>')
                temp_html_text = control.get('temporary_html_text', '<p>I have read the above and agree to the financial and scheduling terms.</p>')
                field['control'] = {
                    'temporary_html_text': temp_html_text,
                    'html_text': html_text,
                    'text': '',
                    'options': options
                }
                break
        
        return spec
    
    @staticmethod
    def slugify(text: str, fallback: str = "field") -> str:
        """Convert text to a valid key slug"""
        if not text or not text.strip():
            return fallback
        
        # Normalize unicode and remove combining characters
        text = unicodedata.normalize("NFKD", text)
        text = "".join(ch for ch in text if not unicodedata.combining(ch))
        
        # Replace non-alphanumeric with underscores and lowercase
        text = re.sub(r"[^a-zA-Z0-9]+", "_", text).strip("_").lower()
        
        return text or fallback