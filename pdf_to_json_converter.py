#!/usr/bin/env python3
"""
PDF to Modento Forms JSON Converter

This script extracts form fields from PDF documents and converts them to 
JSON format compliant with the Modento Forms schema specification.

Usage:
    python pdf_to_json_converter.py <pdf_path> [--output <output_path>]
"""

import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import pdfplumber
from dataclasses import dataclass


@dataclass
class FieldInfo:
    """Information about a detected form field"""
    key: str
    title: str
    field_type: str
    section: str
    optional: bool = True
    control: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.control is None:
            self.control = {}


class ModentoSchemaValidator:
    """Validates and normalizes JSON according to Modento Forms schema"""
    
    VALID_INPUT_TYPES = {"name", "email", "phone", "number", "ssn", "zip", "initials"}
    VALID_DATE_TYPES = {"past", "future", "any"}
    
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
    
    @staticmethod
    def ensure_unique_keys(spec: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Ensure all keys are globally unique"""
        seen = set()
        
        def make_unique(key: str) -> str:
            base = key
            counter = 2
            while key in seen:
                key = f"{base}_{counter}"
                counter += 1
            seen.add(key)
            return key
        
        def process_questions(questions: List[Dict[str, Any]]):
            for q in questions:
                q["key"] = make_unique(q["key"])
                if q.get("type") == "multiradio" and "control" in q:
                    nested = q["control"].get("questions", [])
                    if nested:
                        process_questions(nested)
        
        process_questions(spec)
        return spec
    
    @staticmethod
    def add_signature_if_missing(spec: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Add signature field if not present"""
        has_signature = any(q.get("key") == "signature" for q in spec)
        if not has_signature:
            spec.append({
                "key": "signature",
                "title": "Signature",
                "section": "Signature", 
                "optional": False,
                "type": "signature",
                "control": {}
            })
        return spec
    
    @classmethod
    def validate_and_normalize(cls, spec: List[Dict[str, Any]]) -> Tuple[bool, List[str], List[Dict[str, Any]]]:
        """Validate and normalize a Modento spec"""
        errors = []
        
        if not isinstance(spec, list):
            return False, ["Spec must be a top-level JSON array"], spec
        
        # Ensure unique keys
        spec = cls.ensure_unique_keys(spec)
        
        # Add signature if missing
        spec = cls.add_signature_if_missing(spec)
        
        # Validate each question
        for q in spec:
            if not q.get("key"):
                errors.append("Every question must have a non-empty 'key'")
            
            q_type = q.get("type")
            if not q_type:
                errors.append(f"Question '{q.get('key')}' must have a 'type'")
                continue
                
            # Validate control based on type
            control = q.get("control", {})
            
            if q_type == "input":
                input_type = control.get("input_type")
                if input_type and input_type not in cls.VALID_INPUT_TYPES:
                    control["input_type"] = "name"  # Default fallback
            
            elif q_type == "date":
                input_type = control.get("input_type")
                if input_type and input_type not in cls.VALID_DATE_TYPES:
                    control["input_type"] = "any"  # Default fallback
            
            elif q_type in ["radio", "dropdown"]:
                options = control.get("options", [])
                for opt in options:
                    if not opt.get("value"):
                        opt["value"] = cls.slugify(opt.get("name", "option"))
        
        return len(errors) == 0, errors, spec


class PDFFormFieldExtractor:
    """Extract form fields from PDF documents"""
    
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
        
        self.section_patterns = {
            'patient_info': re.compile(r'patient\s*information', re.IGNORECASE),
            'contact': re.compile(r'contact\s*information', re.IGNORECASE),
            'insurance': re.compile(r'insurance|dental\s*plan', re.IGNORECASE),
            'medical_history': re.compile(r'medical\s*history|health\s*history', re.IGNORECASE),
            'consent': re.compile(r'consent|terms|agreement', re.IGNORECASE),
            'signature': re.compile(r'signature', re.IGNORECASE),
        }
    
    def extract_text_from_pdf(self, pdf_path: Path) -> List[str]:
        """Extract text from all pages of PDF"""
        all_text = []
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        all_text.extend(text.split('\n'))
        except Exception as e:
            print(f"Error reading PDF {pdf_path}: {e}")
            return []
        
        return [line.strip() for line in all_text if line.strip()]
    
    def detect_field_type(self, text: str) -> str:
        """Detect field type based on text content"""
        text_lower = text.lower()
        
        if any(pattern.search(text) for pattern in [
            self.field_patterns['signature']
        ]):
            return 'signature'
        
        if any(pattern.search(text) for pattern in [
            self.field_patterns['date']
        ]):
            return 'date'
        
        if any(pattern.search(text) for pattern in [
            self.field_patterns['email']
        ]):
            return 'input'
        
        if any(pattern.search(text) for pattern in [
            self.field_patterns['phone']
        ]):
            return 'input'
        
        if any(pattern.search(text) for pattern in [
            self.field_patterns['name'], 
            self.field_patterns['address'],
            self.field_patterns['ssn']
        ]):
            return 'input'
        
        # Check for yes/no questions
        if re.search(r'\b(?:yes|no)\b', text_lower) or '?' in text:
            return 'radio'
        
        return 'input'  # Default
    
    def detect_input_type(self, text: str) -> str:
        """Detect specific input type for input fields"""
        text_lower = text.lower()
        
        if self.field_patterns['email'].search(text):
            return 'email'
        elif self.field_patterns['phone'].search(text):
            return 'phone'
        elif 'ssn' in text_lower or 'social security' in text_lower:
            return 'ssn'
        elif 'zip' in text_lower:
            return 'zip'
        elif 'initial' in text_lower and len(text) < 20:
            return 'initials'
        elif re.search(r'\bnumber\b', text_lower):
            return 'number'
        else:
            return 'name'
    
    def detect_section(self, text: str, context_lines: List[str]) -> str:
        """Detect form section based on content and context"""
        # Check current line and surrounding context
        all_text = ' '.join([text] + context_lines[:5])
        
        for section, pattern in self.section_patterns.items():
            if pattern.search(all_text):
                return section.replace('_', ' ').title()
        
        return "General Information"
    
    def parse_inline_fields(self, line: str) -> List[Tuple[str, str]]:
        """Parse multiple fields from a single line"""
        fields = []
        
        # Common patterns for inline fields
        patterns = [
            # "Field Name_______ Field2_______ Field3_______"
            r'([A-Za-z][A-Za-z\s\#\/]{2,30}?)(?:_+|:+|\s{3,})',
            # "Name: First_____ MI___ Last_____"
            r'([A-Za-z][A-Za-z\s\#\/]{1,20}?)(?:_+|:)',
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, line)
            for match in matches:
                field_name = match.group(1).strip()
                if len(field_name) > 1 and not field_name.isupper():
                    # Check if it's not just a separator word
                    if field_name.lower() not in ['and', 'or', 'the', 'of', 'to', 'for', 'in', 'with']:
                        fields.append((field_name, line))
        
        return fields
    
    def extract_checkbox_options(self, line: str) -> List[str]:
        """Extract checkbox options from a line"""
        # Pattern for checkbox options like "□ Option1 □ Option2"
        pattern = r'□\s*([A-Za-z][A-Za-z\s\-/]{1,25}?)(?=\s*□|\s*$)'
        matches = re.findall(pattern, line)
        return [match.strip() for match in matches if match.strip()]
    
    def extract_fields_from_text(self, text_lines: List[str]) -> List[FieldInfo]:
        """Extract form fields from text lines"""
        fields = []
        current_section = "Patient Information Form"
        
        for i, line in enumerate(text_lines):
            # Skip very short lines
            if len(line) < 3:
                continue
            
            # Detect section headers
            line_upper = line.upper()
            if any(header in line_upper for header in [
                'PATIENT INFORMATION', 'CONTACT INFORMATION', 'ADDRESS',
                'EMERGENCY CONTACT', 'INSURANCE', 'DENTAL PLAN', 
                'MEDICAL HISTORY', 'HEALTH HISTORY', 'CHILDREN/MINORS',
                'RESPONSIBLE PARTY', 'CONSENT', 'SIGNATURE', 'PRIMARY DENTAL',
                'SECONDARY DENTAL'
            ]):
                if 'DENTAL PLAN' in line_upper or 'INSURANCE' in line_upper:
                    current_section = "Insurance"
                elif 'MEDICAL' in line_upper or 'HEALTH' in line_upper:
                    current_section = "Medical History"
                elif 'MINOR' in line_upper or 'CHILDREN' in line_upper:
                    current_section = "FOR CHILDREN/MINORS ONLY"
                elif 'EMERGENCY' in line_upper:
                    current_section = "Emergency Contact"
                elif 'SIGNATURE' in line_upper or 'CONSENT' in line_upper:
                    current_section = "Signature"
                elif 'SECONDARY' in line_upper:
                    current_section = "Secondary Dental Plan"
                elif 'PRIMARY' in line_upper:
                    current_section = "Primary Dental Plan"
                else:
                    current_section = "Patient Information Form"
                continue
            
            # Handle checkbox questions (radio buttons)
            checkbox_options = self.extract_checkbox_options(line)
            if checkbox_options and len(checkbox_options) >= 2:
                # Extract the question part before the checkboxes
                question_part = re.split(r'□', line)[0].strip()
                if question_part and len(question_part) > 3:
                    key = ModentoSchemaValidator.slugify(question_part)
                    
                    # Convert checkbox options to proper format
                    options = []
                    for opt in checkbox_options:
                        value = opt.lower()
                        if value in ['yes', 'true']:
                            value = True
                        elif value in ['no', 'false']:
                            value = False
                        options.append({"name": opt, "value": value})
                    
                    field = FieldInfo(
                        key=key,
                        title=question_part,
                        field_type='radio',
                        section=current_section,
                        control={'options': options}
                    )
                    fields.append(field)
                continue
            
            # Parse inline fields from the line
            inline_fields = self.parse_inline_fields(line)
            
            for field_name, full_line in inline_fields:
                # Determine field type
                field_type = self.detect_field_type(field_name)
                
                # Create control based on type
                control = {}
                if field_type == 'input':
                    input_type = self.detect_input_type(field_name)
                    control['input_type'] = input_type
                    if input_type == 'phone':
                        control['phone_prefix'] = '+1'
                    control['hint'] = None
                elif field_type == 'date':
                    if 'birth' in field_name.lower() or 'dob' in field_name.lower():
                        control['input_type'] = 'past'
                    elif 'today' in field_name.lower():
                        control['input_type'] = 'any'
                    else:
                        control['input_type'] = 'past'
                    control['hint'] = None
                elif field_type == 'signature':
                    control = {}
                
                # Handle special cases
                if 'state' in field_name.lower() and 'estate' not in field_name.lower():
                    field_type = 'states'
                    control = {'hint': None, 'input_type': 'name'}
                
                # Create field
                key = ModentoSchemaValidator.slugify(field_name)
                
                field = FieldInfo(
                    key=key,
                    title=field_name,
                    field_type=field_type,
                    section=current_section,
                    control=control
                )
                fields.append(field)
        
        return fields


class PDFToJSONConverter:
    """Main converter class"""
    
    def __init__(self):
        self.extractor = PDFFormFieldExtractor()
        self.validator = ModentoSchemaValidator()
    
    def convert_pdf_to_json(self, pdf_path: Path, output_path: Optional[Path] = None) -> Dict[str, Any]:
        """Convert a PDF to Modento Forms JSON"""
        print(f"Processing PDF: {pdf_path}")
        
        # Extract text from PDF
        text_lines = self.extractor.extract_text_from_pdf(pdf_path)
        if not text_lines:
            raise ValueError(f"Could not extract text from PDF: {pdf_path}")
        
        print(f"Extracted {len(text_lines)} lines of text")
        
        # Extract form fields
        fields = self.extractor.extract_fields_from_text(text_lines)
        print(f"Detected {len(fields)} form fields")
        
        # Convert to Modento format
        json_spec = []
        for field in fields:
            field_dict = {
                "key": field.key,
                "title": field.title,
                "section": field.section,
                "optional": field.optional,
                "type": field.field_type,
                "control": field.control
            }
            json_spec.append(field_dict)
        
        # Validate and normalize
        is_valid, errors, normalized_spec = self.validator.validate_and_normalize(json_spec)
        
        if errors:
            print("Validation warnings:")
            for error in errors:
                print(f"  - {error}")
        
        # Save to file if output path provided
        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(normalized_spec, f, indent=2, ensure_ascii=False)
            print(f"Saved JSON to: {output_path}")
        
        return {
            "spec": normalized_spec,
            "is_valid": is_valid,
            "errors": errors,
            "field_count": len(fields)
        }


def main():
    """Command line interface"""
    parser = argparse.ArgumentParser(description="Convert PDF forms to Modento JSON format")
    parser.add_argument("pdf_path", help="Path to the PDF file")
    parser.add_argument("--output", "-o", help="Output JSON file path")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    pdf_path = Path(args.pdf_path)
    if not pdf_path.exists():
        print(f"Error: PDF file not found: {pdf_path}")
        sys.exit(1)
    
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = pdf_path.with_suffix('.json')
    
    try:
        converter = PDFToJSONConverter()
        result = converter.convert_pdf_to_json(pdf_path, output_path)
        
        print(f"\nConversion complete!")
        print(f"Fields detected: {result['field_count']}")
        print(f"Validation passed: {result['is_valid']}")
        
        if result['errors'] and args.verbose:
            print("\nValidation issues:")
            for error in result['errors']:
                print(f"  - {error}")
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()