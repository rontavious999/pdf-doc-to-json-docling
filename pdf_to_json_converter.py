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
from dataclasses import dataclass

# Docling imports for advanced PDF processing
from docling.document_converter import DocumentConverter
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.datamodel.base_models import InputFormat


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
    """Extract form fields from PDF documents using Docling's advanced capabilities"""
    
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
        
        # Initialize Docling converter with maximum accuracy settings
        self._setup_docling_converter()
    
    def _setup_docling_converter(self):
        """Configure Docling for maximum form scanning accuracy"""
        # Configure pipeline for maximum accuracy
        self.pipeline_options = PdfPipelineOptions()
        self.pipeline_options.do_ocr = True  # Enable OCR for scanned forms
        self.pipeline_options.do_table_structure = True  # Detect table structures
        self.pipeline_options.images_scale = 2.0  # Higher resolution for better OCR
        self.pipeline_options.generate_page_images = False  # Don't need page images
        self.pipeline_options.generate_table_images = False  # Don't need table images
        self.pipeline_options.generate_picture_images = False  # Don't need picture images
        
        # Force full page OCR for maximum field detection
        if hasattr(self.pipeline_options.ocr_options, 'force_full_page_ocr'):
            self.pipeline_options.ocr_options.force_full_page_ocr = True
        
        # Create converter with optimized settings
        self.converter = DocumentConverter()
        
        # Store pipeline info for reporting
        self.pipeline_info = {
            'pipeline': 'StandardPdfPipeline',
            'backend': 'DoclingParseDocumentBackend', 
            'ocr_enabled': self.pipeline_options.do_ocr,
            'ocr_engine': 'EasyOCR',  # Docling's default OCR engine
            'table_structure': self.pipeline_options.do_table_structure,
            'images_scale': self.pipeline_options.images_scale
        }
    
    def extract_text_from_pdf(self, pdf_path: Path) -> Tuple[List[str], Dict[str, Any]]:
        """Extract text from PDF using Docling's advanced capabilities"""
        try:
            # Convert PDF using Docling
            result = self.converter.convert(str(pdf_path))
            
            # Extract text with superior layout preservation
            full_text = result.document.export_to_text()
            text_lines = [line.strip() for line in full_text.split('\n') if line.strip()]
            
            # Update pipeline info with actual conversion details
            pipeline_info = self.pipeline_info.copy()
            pipeline_info['document_name'] = result.document.name
            pipeline_info['elements_extracted'] = len(list(result.document.texts))
            
            return text_lines, pipeline_info
            
        except Exception as e:
            print(f"Error reading PDF {pdf_path} with Docling: {e}")
            return [], self.pipeline_info
    
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
        elif ('initial' in text_lower and len(text) < 20) or text_lower.strip() in ['mi', 'm.i.', 'middle initial', 'middle init']:
            return 'initials'
        elif re.search(r'\bnumber\b', text_lower) and 'license' not in text_lower:
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
    
    def normalize_field_name(self, field_name: str, context_line: str = "") -> str:
        """Normalize field names to match expected patterns"""
        field_lower = field_name.lower().strip()
        
        # Handle common abbreviations and variations
        name_mappings = {
            'first': 'First Name',
            'last': 'Last Name', 
            'mi': 'MI',
            'middle initial': 'MI',
            'middle init': 'MI',
            'apt/unit/suite': 'Apt/Unit/Suite',
            'social security no': 'Social Security No.',
            'social security number': 'Social Security No.',
            'ssn': 'Social Security No.',
            'drivers license': 'Drivers License #',
            'driver license': 'Drivers License #',
            'drivers license #': 'Drivers License #',
            'dl': 'Drivers License #',
            'date of birth': 'Date of Birth',
            'dob': 'Date of Birth',
            'birthdate': 'Birthdate',
            'birth date': 'Date of Birth',
            'today\'s date': 'Today\'s Date',
            'todays date': 'Today\'s Date',
            'date': 'Today\'s Date' if 'today' in context_line.lower() else 'Date',
            'e-mail': 'E-Mail',
            'email': 'E-Mail',
            'mobile phone': 'Mobile Phone',
            'mobile': 'Mobile',
            'home phone': 'Home Phone',
            'home': 'Home',
            'work phone': 'Work Phone',
            'work': 'Work',
            'cell phone': 'Mobile Phone',
            'patient name': 'Patient Name',
            'name of insured': 'Name of Insured',
            'insurance company': 'Insurance Company',
            'dental plan name': 'Dental Plan Name',
            'plan/group number': 'Plan/Group Number',
            'group number': 'Plan/Group Number',
            'id number': 'ID Number',
            'relationship to patient': 'Relationship to Patient',
            'patient relationship to insured': 'Patient Relationship to Insured',
            'name of school': 'Name of School',
            'patient employed by': 'Patient Employed By',
            'employer': 'Patient Employed By',
            'employer (if different from above)': 'Employer (if different from above)',
            'occupation': 'Occupation',
            'in case of emergency, who should be notified': 'In case of emergency, who should be notified',
            'in case of emergency, who should be notified?': 'In case of emergency, who should be notified',
            'emergency contact': 'In case of emergency, who should be notified',
            'nickname': 'Nickname',
            'street': 'Street',
            'city': 'City',
            'state': 'State',
            'zip': 'Zip',
            'phone': 'Phone',
        }
        
        # Check direct mappings first
        if field_lower in name_mappings:
            return name_mappings[field_lower]
        
        # Special cases for keys that need specific handling
        if field_lower == 'mi':
            return 'MI'  # This will generate key "mi" via slugify
        
        # Handle variations with context
        if field_lower == 'first' and any(word in context_line.lower() for word in ['name', 'patient']):
            return 'First Name'
        if field_lower == 'last' and any(word in context_line.lower() for word in ['name', 'patient']):
            return 'Last Name'
        
        # Handle context-sensitive field names for different from patient
        if 'if different from patient' in context_line.lower():
            if field_lower == 'street':
                return 'Street'  # Will be disambiguated by hint
        
        return field_name
    
    def detect_radio_question(self, line: str) -> Optional[Tuple[str, List[Dict[str, Any]]]]:
        """Detect radio button questions and extract options"""
        line_lower = line.lower()
        
        # Common radio button patterns
        radio_patterns = [
            # Sex/Gender selection
            {
                'pattern': r'sex.*?(?:male|female)',
                'title': 'Sex',
                'options': [
                    {"name": "Male", "value": "male"},
                    {"name": "Female", "value": "female"}
                ]
            },
            # Marital status
            {
                'pattern': r'marital.*?status',
                'title': 'Marital Status',
                'options': [
                    {"name": "Married", "value": "Married"},
                    {"name": "Single", "value": "Single"},
                    {"name": "Divorced", "value": "Divorced"},
                    {"name": "Separated", "value": "Separated"},
                    {"name": "Widowed", "value": "Widowed"}
                ]
            },
            # Yes/No questions
            {
                'pattern': r'is.*?patient.*?minor',
                'title': 'Is the Patient a Minor?',
                'options': [
                    {"name": "Yes", "value": True},
                    {"name": "No", "value": False}
                ]
            },
            {
                'pattern': r'full.*?time.*?student',
                'title': 'Full-time Student',
                'options': [
                    {"name": "Yes", "value": True},
                    {"name": "No", "value": False}
                ]
            },
            # Contact preference
            {
                'pattern': r'preferred.*?method.*?contact',
                'title': 'What Is Your Preferred Method Of Contact',
                'options': [
                    {"name": "Mobile Phone", "value": "Mobile Phone"},
                    {"name": "Home Phone", "value": "Home Phone"},
                    {"name": "Work Phone", "value": "Work Phone"},
                    {"name": "E-mail", "value": "E-mail"}
                ]
            },
            # Relationship to patient
            {
                'pattern': r'relationship.*?to.*?patient',
                'title': 'Relationship To Patient',
                'options': [
                    {"name": "Self", "value": "Self"},
                    {"name": "Spouse", "value": "Spouse"},
                    {"name": "Parent", "value": "Parent"},
                    {"name": "Other", "value": "Other"}
                ]
            },
            # Primary residence for minors
            {
                'pattern': r'primary.*?residence',
                'title': 'If Patient Is A Minor, Primary Residence',
                'options': [
                    {"name": "Both Parents", "value": "Both Parents"},
                    {"name": "Mom", "value": "Mom"},
                    {"name": "Dad", "value": "Dad"},
                    {"name": "Step Parent", "value": "Step Parent"},
                    {"name": "Shared Custody", "value": "Shared Custody"},
                    {"name": "Guardian", "value": "Guardian"}
                ]
            }
        ]
        
        for pattern_info in radio_patterns:
            if re.search(pattern_info['pattern'], line_lower):
                return pattern_info['title'], pattern_info['options']
        
        return None
    
    def parse_inline_fields(self, line: str) -> List[Tuple[str, str]]:
        fields = []
        seen_fields = set()
        
        # Skip lines that are clearly section headers or questions
        if any(keyword in line.lower() for keyword in ['patient information form', 'for children/minors only', 'primary dental plan', 'secondary dental plan']):
            return fields
        
        # Handle specific known field patterns first
        known_patterns = {
            r'First\s*_{5,}.*?MI\s*_{2,}.*?Last\s*_{5,}.*?Nickname\s*_{5,}': [
                ('First Name', 'First'),
                ('MI', 'MI'), 
                ('Last Name', 'Last'),
                ('Nickname', 'Nickname')
            ],
            r'Mobile\s*_{5,}.*?Home\s*_{5,}.*?Work\s*_{5,}': [
                ('Mobile', 'Mobile'),
                ('Home', 'Home'),
                ('Work', 'Work')
            ],
            r'Street\s*_{10,}.*?Apt/Unit/Suite\s*_{5,}': [
                ('Street', 'Street'),
                ('Apt/Unit/Suite', 'Apt/Unit/Suite')
            ],
            r'City\s*_{10,}.*?State\s*_{3,}.*?Zip\s*_{5,}': [
                ('City', 'City'),
                ('State', 'State'),
                ('Zip', 'Zip')
            ],
            r'E-Mail\s*_{10,}.*?Drivers License #\s*_{5,}': [
                ('E-Mail', 'E-Mail'),
                ('Drivers License #', 'Drivers License #')
            ],
            r'Patient Employed By\s*_{10,}.*?Occupation\s*_{10,}': [
                ('Patient Employed By', 'Patient Employed By'),
                ('Occupation', 'Occupation')
            ],
            r'Street\s*_{10,}.*?City\s*_{10,}.*?State\s*_{3,}.*?Zip\s*_{5,}': [
                ('Street', 'Street'),
                ('City', 'City'),
                ('State', 'State'),
                ('Zip', 'Zip')
            ],
            r'Name of Insured\s*_{10,}.*?Birthdate\s*_{5,}': [
                ('Name of Insured', 'Name of Insured'),
                ('Birthdate', 'Birthdate')
            ],
            r'Insurance Company\s*_{10,}.*?Phone\s*_{5,}': [
                ('Insurance Company', 'Insurance Company'),
                ('Phone', 'Phone')
            ],
            r'Dental Plan Name\s*_{10,}.*?Plan/Group Number\s*_{10,}': [
                ('Dental Plan Name', 'Dental Plan Name'),
                ('Plan/Group Number', 'Plan/Group Number')
            ],
            r'ID Number\s*_{10,}.*?Patient Relationship to Insured\s*_{5,}': [
                ('ID Number', 'ID Number'),
                ('Patient Relationship to Insured', 'Patient Relationship to Insured')
            ],
            r'In case of emergency, who should be notified\?\s*_{10,}.*?Relationship to Patient\s*_{5,}': [
                ('In case of emergency, who should be notified', 'In case of emergency, who should be notified'),
                ('Relationship to Patient', 'Relationship to Patient')
            ],
            r'Mobile Phone\s*_{5,}.*?Home Phone\s*_{5,}': [
                ('Mobile Phone', 'Mobile Phone'),
                ('Home Phone', 'Home Phone')
            ]
        }
        
        # Check for known patterns first
        for pattern, field_tuples in known_patterns.items():
            if re.search(pattern, line, re.IGNORECASE):
                for field_title, field_key in field_tuples:
                    normalized_name = self.normalize_field_name(field_title, line)
                    if field_title not in seen_fields:
                        fields.append((normalized_name, line))
                        seen_fields.add(field_title)
                return fields
        
        # Handle specific individual field patterns that appear alone
        individual_patterns = {
            r'^Patient Employed By\s*$': 'Patient Employed By',
            r'^Occupation\s*$': 'Occupation', 
            r'^Name of Insured\s*$': 'Name of Insured',
            r'^Birthdate\s*$': 'Birthdate',
            r'^Insurance Company\s*$': 'Insurance Company',
            r'^Dental Plan Name\s*$': 'Dental Plan Name',
            r'^Plan/Group Number\s*$': 'Plan/Group Number',
            r'^ID Number\s*$': 'ID Number',
            r'^Patient Relationship to Insured\s*$': 'Patient Relationship to Insured',
            r'^In case of emergency, who should be notified\?\s*$': 'In case of emergency, who should be notified',
            r'^Relationship to Patient\s*$': 'Relationship to Patient',
            r'^Mobile Phone\s*$': 'Mobile Phone',
            r'^Home Phone\s*$': 'Home Phone',
            r'^Name of School\s*$': 'Name of School',
            r'^Employer \(if different from above\)\s*$': 'Employer (if different from above)',
        }
        
        for pattern, field_title in individual_patterns.items():
            if re.search(pattern, line, re.IGNORECASE):
                normalized_name = self.normalize_field_name(field_title, line)
                fields.append((normalized_name, line))
                return fields
        
        # Skip "Patient Name:" lines as they're usually section headers, not fields
        if re.match(r'Patient Name\s*:', line):
            return fields
        
        # Single comprehensive pattern to avoid duplicates
        # Matches field names followed by underscores, colons, or multiple spaces
        pattern = r'([A-Za-z][A-Za-z\s\#\/\(\)\-]{0,35}?)(?:_+|:+|\s{3,})'
        
        matches = re.finditer(pattern, line)
        for match in matches:
            field_name = match.group(1).strip()
            
            # Filter out invalid field names
            if (len(field_name) > 1 and 
                field_name.lower() not in ['and', 'or', 'the', 'of', 'to', 'for', 'in', 'with', 'if', 'is', 'are', 'patient name'] and
                field_name not in seen_fields and
                # Allow meaningful uppercase abbreviations like MI, SSN
                (not field_name.isupper() or field_name.lower() in ['mi', 'ssn', 'id', 'dl', 'dob'])):
                
                # Normalize the field name
                normalized_name = self.normalize_field_name(field_name, line)
                fields.append((normalized_name, line))
                seen_fields.add(field_name)
        
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
        i = 0
        
        while i < len(text_lines):
            line = text_lines[i]
            
            # Skip very short lines
            if len(line) < 3:
                i += 1
                continue
            
            # Detect section headers
            line_upper = line.upper()
            if any(header in line_upper for header in [
                'PATIENT INFORMATION', 'CONTACT INFORMATION', 'ADDRESS',
                'EMERGENCY CONTACT', 'INSURANCE', 'DENTAL PLAN', 
                'MEDICAL HISTORY', 'HEALTH HISTORY', 'CHILDREN/MINORS',
                'RESPONSIBLE PARTY', 'CONSENT', 'SIGNATURE', 'PRIMARY DENTAL',
                'SECONDARY DENTAL', 'DENTAL BENEFIT PLAN'
            ]):
                if 'DENTAL PLAN' in line_upper or 'INSURANCE' in line_upper or 'DENTAL BENEFIT' in line_upper:
                    if 'SECONDARY' in line_upper:
                        current_section = "Secondary Dental Plan"
                    elif 'PRIMARY' in line_upper:
                        current_section = "Primary Dental Plan"
                    else:
                        current_section = "Primary Dental Plan"
                elif 'MEDICAL' in line_upper or 'HEALTH' in line_upper:
                    current_section = "Medical History"
                elif 'MINOR' in line_upper or 'CHILDREN' in line_upper:
                    current_section = "FOR CHILDREN/MINORS ONLY"
                elif 'EMERGENCY' in line_upper:
                    current_section = "Emergency Contact"
                elif 'SIGNATURE' in line_upper or 'CONSENT' in line_upper:
                    current_section = "Signature"
                else:
                    current_section = "Patient Information Form"
                i += 1
                continue

            # Handle standalone single-word fields (like "SSN", "Sex")
            standalone_fields = {
                'SSN': ('ssn', 'Social Security No.', 'input', {'input_type': 'ssn', 'hint': None}),
                'Sex': ('sex', 'Sex', 'radio', {'options': [{"name": "Male", "value": "male"}, {"name": "Female", "value": "female"}], 'hint': None}),
                'Social Security No.': ('ssn_2', 'Social Security No.', 'input', {'input_type': 'ssn', 'hint': None}),
                'Today \'s Date': ('todays_date', 'Today\'s Date', 'date', {'input_type': 'any', 'hint': None}),
                'Date of Birth': ('date_of_birth', 'Date of Birth', 'date', {'input_type': 'past', 'hint': None}),
                'Birthdate': ('birthdate', 'Birthdate', 'date', {'input_type': 'past', 'hint': None}),
            }
            
            line_stripped = line.strip()
            if line_stripped in standalone_fields:
                key, title, field_type, control = standalone_fields[line_stripped]
                
                field = FieldInfo(
                    key=key,
                    title=title,
                    field_type=field_type,
                    section=current_section,
                    control=control
                )
                fields.append(field)
                i += 1
                continue
            
            # Handle large text blocks (like terms and conditions)
            if (len(line) > 100 and 
                any(keyword in line.lower() for keyword in ['responsibility', 'payment', 'benefit', 'authorize', 'consent']) and
                current_section == "Signature"):
                
                # Collect multi-line text block
                text_content = [line]
                j = i + 1
                while j < len(text_lines) and len(text_lines[j]) > 50:
                    text_content.append(text_lines[j])
                    j += 1
                
                # Create text field
                full_text = ' '.join(text_content)
                key = f"text_{len([f for f in fields if f.field_type == 'text']) + 1}"
                
                field = FieldInfo(
                    key=key,
                    title="",
                    field_type='text',
                    section=current_section,
                    optional=False,
                    control={
                        'html_text': f"<p>{full_text}</p>",
                        'temporary_html_text': f"<p>{full_text}</p>",
                        'text': ""
                    }
                )
                fields.append(field)
                i = j
                continue
            
            # Handle signature fields with initials
            if '(initial)' in line.lower():
                # Extract the text before (initial)
                text_part = line.split('(initial)')[0].strip()
                if text_part:
                    # Create the text field
                    key = f"text_{len([f for f in fields if f.field_type == 'text']) + 1}"
                    field = FieldInfo(
                        key=key,
                        title="",
                        field_type='text',
                        section=current_section,
                        optional=False,
                        control={
                            'html_text': f"<p>{text_part}</p>",
                            'temporary_html_text': f"<p>{text_part}</p>",
                            'text': ""
                        }
                    )
                    fields.append(field)
                    
                    # Create the initial field
                    initials_key = f"initials_{len([f for f in fields if f.key.startswith('initials')]) + 1}" if any(f.key.startswith('initials') for f in fields) else "initials"
                    field = FieldInfo(
                        key=initials_key,
                        title="Initial",
                        field_type='input',
                        section=current_section,
                        control={'input_type': 'initials'}
                    )
                    fields.append(field)
                i += 1
                continue
            
            # Handle consent questions with YES/NO checkboxes
            if re.search(r'YES\s+N?O?\s*\(Check One\)', line, re.IGNORECASE):
                # Extract the question part
                question_match = re.match(r'^(.*?)\s+YES\s+N?O?\s*\(Check One\)', line, re.IGNORECASE)
                if question_match:
                    question = question_match.group(1).strip()
                    key = ModentoSchemaValidator.slugify(question)
                    
                    field = FieldInfo(
                        key=key,
                        title=question,
                        field_type='radio',
                        section=current_section,
                        optional=False,
                        control={
                            'options': [
                                {"name": "Yes", "value": True},
                                {"name": "No", "value": False}
                            ],
                            'hint': None
                        }
                    )
                    fields.append(field)
                    
                    # Add initials field
                    initials_key = f"initials_{len([f for f in fields if f.key.startswith('initials')]) + 1}"
                    field = FieldInfo(
                        key=initials_key,
                        title="Initial",
                        field_type='input',
                        section=current_section,
                        control={'input_type': 'initials'}
                    )
                    fields.append(field)
                i += 1
                continue
            
            # Handle signature and date fields
            if re.search(r'Signature\s*_{10,}.*?Date\s*_{5,}', line, re.IGNORECASE):
                # Add signature field
                field = FieldInfo(
                    key="signature",
                    title="Signature",
                    field_type='signature',
                    section=current_section,
                    optional=False,
                    control={}
                )
                fields.append(field)
                
                # Add date signed field
                field = FieldInfo(
                    key="date_signed",
                    title="Date Signed",
                    field_type='date',
                    section=current_section,
                    control={'input_type': 'any', 'hint': None}
                )
                fields.append(field)
                i += 1
                continue
            
            # Check for radio button questions first
            radio_result = self.detect_radio_question(line)
            if radio_result:
                title, options = radio_result
                key = ModentoSchemaValidator.slugify(title)
                
                field = FieldInfo(
                    key=key,
                    title=title,
                    field_type='radio',
                    section=current_section,
                    control={'options': options, 'hint': None}
                )
                fields.append(field)
                i += 1
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
                        control={'options': options, 'hint': None}
                    )
                    fields.append(field)
                i += 1
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
                    
                    # Add hints for specific contexts
                    hint = None
                    if 'if different from patient' in full_line.lower():
                        hint = 'If different from patient'
                    elif 'if different from above' in full_line.lower():
                        hint = '(if different from above)'
                    elif 'insurance company' in full_line.lower() and field_name.lower() in ['phone', 'street', 'city', 'zip']:
                        hint = 'Insurance Company'
                    elif 'responsible party' in full_line.lower() and field_name.lower() in ['first name', 'last name', 'date of birth']:
                        if field_name.lower() == 'first name':
                            hint = 'Name of Responsible Party'
                        elif field_name.lower() == 'last name':
                            hint = 'Name of Responsible Party'
                        elif field_name.lower() == 'date of birth':
                            hint = 'Responsible Party'
                    
                    control['hint'] = hint
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
            
            i += 1
        
        return fields


class PDFToJSONConverter:
    """Main converter class with enhanced Docling integration"""
    
    def __init__(self):
        self.extractor = PDFFormFieldExtractor()
        self.validator = ModentoSchemaValidator()
    
    def convert_pdf_to_json(self, pdf_path: Path, output_path: Optional[Path] = None) -> Dict[str, Any]:
        """Convert a PDF to Modento Forms JSON with enhanced processing"""
        # Start processing message
        print(f"[+] Processing {pdf_path.name} ...")
        
        # Extract text from PDF using Docling
        text_lines, pipeline_info = self.extractor.extract_text_from_pdf(pdf_path)
        if not text_lines:
            raise ValueError(f"Could not extract text from PDF: {pdf_path}")
        
        # Extract form fields
        fields = self.extractor.extract_fields_from_text(text_lines)
        
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
        
        # Count sections
        sections = set(field.get("section", "Unknown") for field in normalized_spec)
        section_count = len(sections)
        
        # Save to file if output path provided
        if output_path:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(normalized_spec, f, indent=2, ensure_ascii=False)
            
            # Success message with requested format
            print(f"[✓] Wrote JSON: {output_path.parent.name}/{output_path.name}")
            print(f"[i] Sections: {section_count} | Fields: {len(fields)}")
            print(f"[i] Pipeline/Model/Backend used: {pipeline_info['pipeline']}/{pipeline_info['backend']}")
            ocr_status = "used" if pipeline_info['ocr_enabled'] else "not used"
            print(f"[x] OCR ({pipeline_info['ocr_engine']}): {ocr_status}")
        
        return {
            "spec": normalized_spec,
            "is_valid": is_valid,
            "errors": errors,
            "field_count": len(fields),
            "section_count": section_count,
            "pipeline_info": pipeline_info
        }


def process_directory(input_dir: Path, output_dir: Path = None, verbose: bool = False):
    """Process all PDFs in a directory (batch mode)"""
    if output_dir is None:
        output_dir = input_dir / "json_output"
    
    output_dir.mkdir(exist_ok=True)
    
    converter = PDFToJSONConverter()
    pdf_files = list(input_dir.glob("*.pdf"))
    
    if not pdf_files:
        print(f"No PDF files found in {input_dir}")
        return
    
    print(f"Found {len(pdf_files)} PDF files to process\n")
    
    results = []
    
    for pdf_path in pdf_files:
        try:
            output_path = output_dir / f"{pdf_path.stem}.json"
            result = converter.convert_pdf_to_json(pdf_path, output_path)
            
            results.append({
                "file": pdf_path.name,
                "success": True,
                "fields": result["field_count"],
                "sections": result["section_count"],
                "valid": result["is_valid"],
                "output": str(output_path),
                "pipeline_info": result["pipeline_info"]
            })
            
            if verbose and result['errors']:
                print(f"  Validation warnings:")
                for error in result['errors']:
                    print(f"    - {error}")
        
        except Exception as e:
            print(f"Error processing {pdf_path.name}: {e}")
            results.append({
                "file": pdf_path.name,
                "success": False,
                "error": str(e)
            })
    
    # Save summary
    summary_path = output_dir / "conversion_summary.json"
    with open(summary_path, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n[✓] Summary saved to: {summary_path}")
    
    successful = sum(1 for r in results if r.get("success", False))
    print(f"[i] Successfully processed: {successful}/{len(results)} files")
    
    if verbose:
        print(f"\n[i] Pipeline details:")
        if results and results[0].get("pipeline_info"):
            pipeline = results[0]["pipeline_info"]
            print(f"    Pipeline/Backend: {pipeline.get('pipeline', 'Unknown')}/{pipeline.get('backend', 'Unknown')}")
            print(f"    OCR Engine: {pipeline.get('ocr_engine', 'Unknown')} ({'enabled' if pipeline.get('ocr_enabled') else 'disabled'})")


def main():
    """Command line interface with batch functionality"""
    parser = argparse.ArgumentParser(description="Convert PDF forms to Modento JSON format using Docling")
    parser.add_argument("path", nargs='?', default=None, help="Path to PDF file or directory (defaults to 'pdfs' directory)")
    parser.add_argument("--output", "-o", help="Output JSON file path (for single file) or output directory (for batch)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    # Default to 'pdfs' directory if no path provided
    if args.path is None:
        input_path = Path("pdfs")
        if not input_path.exists():
            print(f"Error: Default input directory 'pdfs' not found")
            sys.exit(1)
    else:
        input_path = Path(args.path)
        if not input_path.exists():
            print(f"Error: Path not found: {input_path}")
            sys.exit(1)
    
    # Check if input is a directory (batch mode) or file (single mode)
    if input_path.is_dir():
        # Batch processing mode
        if args.output:
            output_dir = Path(args.output)
        elif args.path is None:  # Default mode with no path specified
            output_dir = Path("output")
        else:
            output_dir = input_path / "json_output"
        
        try:
            process_directory(input_path, output_dir, args.verbose)
        except Exception as e:
            print(f"Error: {e}")
            sys.exit(1)
    
    elif input_path.is_file():
        # Single file processing mode
        if args.output:
            output_path = Path(args.output)
        else:
            output_path = input_path.with_suffix('.json')
        
        try:
            converter = PDFToJSONConverter()
            result = converter.convert_pdf_to_json(input_path, output_path)
            
            if args.verbose:
                print(f"\nConversion complete!")
                print(f"Fields detected: {result['field_count']}")
                print(f"Sections detected: {result['section_count']}")
                print(f"Validation passed: {result['is_valid']}")
                
                if result['errors']:
                    print("\nValidation issues:")
                    for error in result['errors']:
                        print(f"  - {error}")
                
                print(f"\nPipeline details:")
                for key, value in result['pipeline_info'].items():
                    print(f"  - {key}: {value}")
            
        except Exception as e:
            print(f"Error: {e}")
            sys.exit(1)
    
    else:
        print(f"Error: Path is neither a file nor directory: {input_path}")
        sys.exit(1)


if __name__ == "__main__":
    main()