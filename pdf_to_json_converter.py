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
    line_idx: int = 0  # For ordering preservation
    
    def __post_init__(self):
        if self.control is None:
            self.control = {}


class ModentoSchemaValidator:
    """Validates and normalizes JSON according to Modento Forms schema"""
    
    VALID_TYPES = {"input", "radio", "checkbox", "dropdown", "states", "date", "signature", "initials", "text", "header"}
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
        """Ensure all keys are globally unique with context-aware deduplication"""
        seen = set()
        to_remove = []  # Track indices to remove
        
        def make_unique(key: str) -> str:
            base = key
            counter = 2
            while key in seen:
                key = f"{base}_{counter}"
                counter += 1
            seen.add(key)
            return key
        
        def should_merge_or_remove(current_idx: int, spec: List[Dict[str, Any]]) -> Optional[int]:
            """Check if current field should be merged with or removed in favor of a previous field"""
            current = spec[current_idx]
            current_key = current.get("key", "")
            current_title = current.get("title", "")
            current_section = current.get("section", "")
            
            # Look for existing field with same title in reasonable section
            for prev_idx in range(current_idx):
                prev = spec[prev_idx]
                prev_title = prev.get("title", "")
                prev_section = prev.get("section", "")
                
                # If same title and compatible section, consider merging/removing
                if (prev_title == current_title and 
                    current_title and  # Don't merge empty titles
                    prev_title and
                    len(current_title) > 2):  # Don't merge very short titles
                    
                    # Same section - likely duplicate
                    if prev_section == current_section:
                        return prev_idx
                    
                    # Related sections that could indicate same logical field
                    patient_sections = ["Patient Information", "Patient Info", "Patient Information Form"]
                    if (prev_section in patient_sections and current_section in patient_sections):
                        return prev_idx
                        
            return None
        
        # First pass: identify and mark duplicates for removal
        i = 0
        while i < len(spec):
            merge_with = should_merge_or_remove(i, spec)
            if merge_with is not None:
                # Keep the one in the better section, or the first one if same section
                current = spec[i]
                prev = spec[merge_with]
                
                # Prefer "Patient Information" over "Patient Information Form"
                if (current.get("section") == "Patient Information" and 
                    prev.get("section") == "Patient Information Form"):
                    # Remove previous, keep current
                    to_remove.append(merge_with)
                else:
                    # Remove current, keep previous
                    to_remove.append(i)
            i += 1
        
        # Remove duplicates (in reverse order to maintain indices)
        for idx in sorted(to_remove, reverse=True):
            spec.pop(idx)
        
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

        # 1) rename any existing signature to key='signature' (first one wins)
        seen_signature = False
        for q in spec:
            if q.get("type") == "signature":
                if not seen_signature:
                    q["key"] = "signature"
                    seen_signature = True
                else:
                    # drop subsequent signature controls
                    q["__drop__"] = True

        spec = [q for q in spec if not q.get("__drop__")]

        # 2) if none exists, add one
        if not any(q.get("type") == "signature" for q in spec):
            spec.append({"key":"signature","title":"Signature","section":"Signature","optional":False,"type":"signature","control":{}})

        # 3) ensure unique keys (but keep 'signature' stable)
        spec = cls.ensure_unique_keys(spec)

        # 4) per-question checks & normalizations
        for q in spec:
            q_type = q.get("type")
            if q_type not in cls.VALID_TYPES:
                errors.append(f"Unknown type '{q_type}' on key '{q.get('key')}'")
                continue

            ctrl = q.setdefault("control", {})
            # move hint to control.extra.hint
            if "hint" in ctrl:
                hint = ctrl.pop("hint")
                if hint:
                    extra = ctrl.setdefault("extra", {})
                    extra["hint"] = hint

            if q_type == "input":
                t = ctrl.get("input_type")
                if t not in {"name","email","phone","number","ssn","zip"}:
                    ctrl["input_type"] = "name"

            if q_type == "date":
                t = ctrl.get("input_type")
                if t not in {"past","future","any"}:
                    ctrl["input_type"] = "any"

            if q_type == "states":
                # must not carry input_type
                ctrl.pop("input_type", None)

            if q_type in {"radio","checkbox","dropdown"}:
                opts = ctrl.get("options", [])
                for opt in opts:
                    # coerce boolean values to strings
                    v = opt.get("value")
                    if isinstance(v, bool):
                        opt["value"] = "Yes" if v else "No"
                    if not opt.get("value"):
                        opt["value"] = cls.slugify(opt.get("name","option"))

        return (len(errors) == 0), errors, spec


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
    
    def is_field_required(self, field_name: str, section: str, context: str = "") -> bool:
        """Determine if a field should be required based on dental form conventions"""
        field_lower = field_name.lower()
        context_lower = context.lower()
        
        # Essential patient identification fields
        if any(keyword in field_lower for keyword in ['first name', 'last name', 'date of birth', 'birthdate']):
            return True
        
        # Required contact information for main patient
        if (field_lower in ['phone', 'mobile phone', 'mobile'] or 'e-mail' in field_lower) and section == "Patient Information Form":
            return True
        
        # Required address fields for main patient
        if (field_lower in ['street', 'city', 'state', 'zip'] and 
            section == "Patient Information Form" and 
            'if different' not in context_lower):
            return True
        
        # Required SSN and drivers license for main patient  
        if field_lower in ['social security no.', 'ssn', 'drivers license #'] and section == "Patient Information Form":
            return True
        
        # Required demographic fields
        if field_lower in ['sex', 'marital status'] and section == "Patient Information Form":
            return True
        
        # Required emergency contact info
        if field_lower in ['in case of emergency, who should be notified', 'relationship to patient'] and section == "Patient Information Form":
            return True
        
        # Insurance fields are generally required
        if section in ["Primary Dental Plan", "Secondary Dental Plan"]:
            if any(keyword in field_lower for keyword in [
                'name of insured', 'birthdate', 'ssn', 'social security', 'insurance company',
                'dental plan name', 'plan/group number', 'id number', 'patient relationship to insured'
            ]):
                return True
        
        # Children/minor section fields
        if section == "FOR CHILDREN/MINORS ONLY":
            if any(keyword in field_lower for keyword in [
                'is the patient a minor', 'first name', 'last name', 'date of birth',
                'relationship to patient', 'primary residence'
            ]):
                return True
        
        # Signature is always required
        if 'signature' in field_lower:
            return True
        
        # Today's date is required
        if 'today' in field_lower and 'date' in field_lower:
            return True
        
        # Optional fields
        if any(keyword in field_lower for keyword in [
            'nickname', 'mi', 'middle initial', 'apt/unit/suite', 'work phone', 'home phone',
            'occupation', 'employer', 'school', 'home', 'work'
        ]):
            return False
        
        # Context-specific optional fields
        if 'if different' in context_lower or 'optional' in context_lower:
            return False
        
        # Secondary insurance fields are typically optional
        if section == "Secondary Dental Plan":
            return False
        
        # Default to required for main fields, optional for others
        if section == "Patient Information Form":
            return True
        else:
            return False
    
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
        
        # Number detection - for IDs, license numbers, etc.
        elif (any(word in text_lower for word in ['number', 'id', '#']) 
              and 'license' not in text_lower 
              and 'phone' not in text_lower):
            return 'number'
        
        # Default to name for most other fields
        else:
            return 'name'
    
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
            "Primary Dental Plan": ["primary dental plan", "dental benefit plan information primary"],
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
    
    def normalize_field_name(self, field_name: str, context_line: str = "") -> str:
        """Normalize field names to match expected patterns"""
        field_lower = field_name.lower().strip()
        
        # Handle common abbreviations and variations
        name_mappings = {
            'first': 'First Name',
            'last': 'Last Name', 
            'mi': 'Middle Initial',
            'middle init': 'Middle Initial',
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
        
        # Special case for MI to ensure it becomes "Middle Initial"
        if field_lower == 'mi':
            return 'Middle Initial'
        
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
        
        # Skip lines that are just separators or decorative
        if re.match(r'^[_\-\s]*$', line) or len(line.strip()) < 3:
            return fields
        
        # Handle specific known field patterns first - these are comprehensive line patterns
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
            # Context-aware city/state/zip patterns
            r'Street\s*_{10,}.*?City\s*_{10,}.*?State\s*_{3,}.*?Zip\s*_{5,}': [
                ('Street', 'Street'),
                ('City', 'City'),
                ('State', 'State'),
                ('Zip', 'Zip')
            ],
            r'City\s*_{10,}.*?State\s*_{3,}.*?Zip\s*_{5,}': [
                ('City', 'City'),
                ('State', 'State'),
                ('Zip', 'Zip')
            ],
            # Work address specific pattern
            r'Street\s*_{8,}.*?City\s*_{5,}.*?State\s*_{3,}.*?Zip\s*_{3,}': [
                ('Street', 'Street'),
                ('City', 'City'),
                ('State', 'State'),
                ('Zip', 'Zip')
            ],
            r'E-Mail\s*_{10,}.*?Drivers License #': [
                ('E-Mail', 'E-Mail'),
                ('Drivers License #', 'Drivers License #')
            ],
            r'Patient Employed By\s*_{10,}.*?Occupation\s*_{10,}': [
                ('Patient Employed By', 'Patient Employed By'),
                ('Occupation', 'Occupation')
            ],
            r'Name of Insured\s*_{10,}.*?Birthdate\s*_{5,}': [
                ('Name of Insured', 'Name of Insured'),
                ('Birthdate', 'Birthdate')
            ],
            r'Insurance Company\s*_{10,}.*?Phone': [
                ('Insurance Company', 'Insurance Company'),
                ('Phone', 'Phone')
            ],
            r'Dental Plan Name\s*_{10,}.*?Plan/Group Number': [
                ('Dental Plan Name', 'Dental Plan Name'),
                ('Plan/Group Number', 'Plan/Group Number')
            ],
            r'ID Number\s*_{10,}.*?Patient Relationship to Insured': [
                ('ID Number', 'ID Number'),
                ('Patient Relationship to Insured', 'Patient Relationship to Insured')
            ],
            r'In case of emergency, who should be notified\?\s*_{10,}.*?Relationship to Patient': [
                ('In case of emergency, who should be notified', 'In case of emergency, who should be notified'),
                ('Relationship to Patient', 'Relationship to Patient')
            ],
            r'Mobile Phone\s*_{5,}.*?Home Phone': [
                ('Mobile Phone', 'Mobile Phone'),
                ('Home Phone', 'Home Phone')
            ]
        }
        
        # Check for known patterns first - these take precedence
        for pattern, field_tuples in known_patterns.items():
            if re.search(pattern, line, re.IGNORECASE):
                for field_title, field_key in field_tuples:
                    normalized_name = self.normalize_field_name(field_title, line)
                    if field_title not in seen_fields:
                        fields.append((normalized_name, line))
                        seen_fields.add(field_title)
                return fields  # Return early for known patterns to avoid duplicates
        
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
            r'^No Name of School\s*$': 'Name of School',  # Handle OCR issue
            r'^Employer \(if different from above\)\s*$': 'Employer (if different from above)',
            # Handle section headers that should create fields
            r'^Work Address:\s*$': None,  # Skip - this is a section header
            r'^Address:\s*$': None,  # Skip - this is a section header  
            r'^Phone:\s*$': None,  # Skip - this is a section header
        }
        
        for pattern, field_title in individual_patterns.items():
            if re.search(pattern, line, re.IGNORECASE):
                if field_title is None:  # Skip section headers
                    return fields
                normalized_name = self.normalize_field_name(field_title, line)
                fields.append((normalized_name, line))
                return fields
        
        # Skip common non-field patterns that could be mistaken for fields
        skip_patterns = [
            r'Patient Name\s*:',
            r'Responsible Party\s*:',
            r'Insurance Information\s*:',
            r'Address\s*:',
            r'[A-Z][A-Z\s]{20,}',  # All caps long text (likely headers)
            r'^\d+\.\s',  # Numbered lists
            r'Please\s+',  # Instructions
            r'Check\s+all\s+that\s+apply',  # Instructions
        ]
        
        for skip_pattern in skip_patterns:
            if re.search(skip_pattern, line, re.IGNORECASE):
                return fields
        
        # Improved pattern to avoid over-detection of fields
        # Only match if there's a clear field structure with sufficient underscores
        pattern = r'([A-Za-z][A-Za-z\s\#\/\(\)\-\.]{1,35}?)(?:_{4,}|:\s*_{2,})'
        
        matches = re.finditer(pattern, line)
        for match in matches:
            field_name = match.group(1).strip()
            
            # More restrictive filtering to avoid false positives
            if (len(field_name) >= 2 and 
                len(field_name) <= 35 and
                field_name.lower() not in [
                    'and', 'or', 'the', 'of', 'to', 'for', 'in', 'with', 'if', 'is', 'are', 
                    'patient name', 'please', 'check', 'all', 'that', 'apply', 'form',
                    'information', 'section', 'date', 'time', 'page'
                ] and
                field_name not in seen_fields and
                # Allow meaningful uppercase abbreviations
                (not field_name.isupper() or field_name.lower() in ['mi', 'ssn', 'id', 'dl', 'dob']) and
                # Avoid detecting repeated characters as fields
                not re.match(r'^(.)\1+$', field_name.replace(' ', '')) and
                # Must contain at least one letter
                re.search(r'[A-Za-z]', field_name)):
                
                # Normalize the field name
                normalized_name = self.normalize_field_name(field_name, line)
                fields.append((normalized_name, line))
                seen_fields.add(field_name)
        
        return fields
    
    def collect_checkbox_run(self, lines: List[str], i: int) -> Tuple[List[Dict[str, Any]], int]:
        """Collect contiguous checkbox/bullet list items"""
        opts = []
        j = i
        check_pat = re.compile(r'^(?:[\u25A1\u25A2\u2610\[\]\(\)]\s*)?([A-Za-z][A-Za-z0-9\-\s\/&]{2,})$')
        while j < len(lines):
            m = check_pat.match(lines[j])
            if not m: 
                break
            label = m.group(1).strip().rstrip(':')
            if len(label) > 2:
                opts.append({"name": label, "value": label})
            j += 1
        return opts, j

    def emit_consent_block(self, title: str, paragraph_lines: List[str], section: str, line_idx: int = 0) -> List[FieldInfo]:
        """Create consent text block with acknowledgment and signature"""
        text_html = "<p>" + " ".join(paragraph_lines) + "</p>"
        return [
            FieldInfo(
                key=ModentoSchemaValidator.slugify(title),
                title=title,
                field_type="text",
                section=section,
                optional=True,
                control={
                    "html_text": text_html,
                    "temporary_html_text": text_html,
                    "text": ""
                },
                line_idx=line_idx
            ),
            FieldInfo(
                key="acknowledge",
                title="I have read and understand the information above.",
                field_type="checkbox",
                section=section,
                optional=False,
                control={"options": [{"name": "I agree", "value": "I agree"}]},
                line_idx=line_idx + 1
            ),
            FieldInfo(
                key="signature",
                title="Signature",
                field_type="signature",
                section="Signature",
                optional=False,
                control={},
                line_idx=line_idx + 2
            ),
            FieldInfo(
                key="signature_date",
                title="Date",
                field_type="date",
                section="Signature",
                optional=False,
                control={"input_type": "any"},
                line_idx=line_idx + 3
            )
        ]

    def looks_like_first_history_item(self, line: str) -> bool:
        """Check if line looks like the first item in a medical history list"""
        # Look for checkbox patterns or bullet patterns common in medical history
        patterns = [
            r'^[\u25A1\u25A2\u2610\[\]\(\)]\s*[A-Za-z]',  # checkbox + text
            r'^[•\-\*]\s*[A-Za-z]',  # bullet + text
            r'^[A-Za-z][A-Za-z\s]{2,}$'  # plain text that could be medical condition
        ]
        return any(re.match(pattern, line) for pattern in patterns)

    def format_text_as_html(self, text: str) -> str:
        """Format text with proper HTML paragraph structure"""
        # Split into sentences and group into logical paragraphs
        sentences = text.split('.')
        paragraphs = []
        current_paragraph = []
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
                
            # Add period back unless it's the last sentence
            if not sentence.endswith((':', '!', '?')):
                sentence += '.'
                
            current_paragraph.append(sentence)
            
            # Start new paragraph at section headers or after certain patterns
            if (any(header in sentence for header in [
                'Patient Responsibilities:', 'Payment:', 'Dental Benefit Plans:', 
                'Scheduling of Appointments:', 'Authorizations:'
            ]) or len(' '.join(current_paragraph)) > 400):
                if current_paragraph:
                    paragraphs.append(' '.join(current_paragraph))
                    current_paragraph = []
        
        # Add remaining sentences
        if current_paragraph:
            paragraphs.append(' '.join(current_paragraph))
        
        # Format as HTML with proper paragraph tags and emphasis
        html_parts = []
        for paragraph in paragraphs:
            if not paragraph.strip():
                continue
                
            # Add emphasis to section headers
            formatted_paragraph = paragraph
            for header in ['Patient Responsibilities:', 'Payment:', 'Dental Benefit Plans:', 
                          'Scheduling of Appointments:', 'Authorizations:']:
                if header in formatted_paragraph:
                    formatted_paragraph = formatted_paragraph.replace(header, f'<strong>{header}</strong>')
            
            # Add emphasis to important notices
            formatted_paragraph = re.sub(
                r'(Payment is due at the time services are rendered|With less than 24 hour notice[^.]*\.)',
                r'<strong>\1</strong>',
                formatted_paragraph
            )
            
            # Add emphasis to "IS" and "IS NOT" choices
            formatted_paragraph = re.sub(
                r'\b(IS)\s+(IS NOT)\s+\(check one\)',
                r'<strong>\1 </strong><strong>\2 (check one) </strong>',
                formatted_paragraph,
                flags=re.IGNORECASE
            )
            
            html_parts.append(f'<p>{formatted_paragraph}</p>')
            
            # Add line breaks between major sections
            if any(header in paragraph for header in [
                'Patient Responsibilities:', 'Dental Benefit Plans:', 
                'Scheduling of Appointments:', 'Authorizations:'
            ]):
                html_parts.append('<p><br></p>')
        
        return ''.join(html_parts)

    def extract_checkbox_options(self, line: str) -> List[str]:
        """Extract checkbox options from a line"""
        # Pattern for checkbox options like "□ Option1 □ Option2"
        pattern = r'□\s*([A-Za-z][A-Za-z\s\-/]{1,25}?)(?=\s*□|\s*$)'
        matches = re.findall(pattern, line)
        return [match.strip() for match in matches if match.strip()]
    
    def post_process_fields(self, fields: List[FieldInfo]) -> List[FieldInfo]:
        """Post-process fields to fix specific extraction issues"""
        processed_fields = []
        
        for field in fields:
            # Handle authorization text field that should be split into radio + initials
            if (field.field_type == 'text' and 
                field.section == 'Signature' and 
                'personal information necessary to process' in field.control.get('html_text', '')):
                
                # Extract the question text (before YES N O)
                html_text = field.control.get('html_text', '')
                if 'YES' in html_text and 'N O' in html_text:
                    # Split at YES N O
                    question_part = html_text.split('YES')[0].strip()
                    # Clean up HTML tags for title
                    question_title = re.sub(r'<[^>]+>', '', question_part).strip()
                    
                    # Create radio field
                    radio_field = FieldInfo(
                        key="i_authorize_the_release_of_my_personal_information_necessary_to_process_my_dental_benefit_claims,_including_health_information,_",
                        title=question_title,
                        field_type='radio',
                        section=field.section,
                        optional=False,
                        control={
                            'options': [
                                {"name": "Yes", "value": True},
                                {"name": "No", "value": False}
                            ],
                            'hint': None,
                            'text': "",
                            'html_text': question_part,
                            'temporary_html_text': question_part
                        }
                    )
                    processed_fields.append(radio_field)
                    
                    # Create initials field
                    initials_field = FieldInfo(
                        key="initials_3",
                        title="Initial",
                        field_type='input',
                        section=field.section,
                        optional=False,
                        control={'input_type': 'initials'}
                    )
                    processed_fields.append(initials_field)
                    continue  # Skip the original text field
            
            processed_fields.append(field)
        
        return processed_fields

    def extract_fields_from_text(self, text_lines: List[str]) -> List[FieldInfo]:
        """Extract form fields from text lines with improved section tracking"""
        fields = []
        current_section = "Patient Information Form"
        i = 0
        
        # Track field occurrences for numbering duplicates
        field_counters = {}
        
        while i < len(text_lines):
            line = text_lines[i]
            
            # Skip very short lines
            if len(line) < 3:
                i += 1
                continue
            
            # Detect section headers - improved pattern matching
            line_upper = line.upper()
            if line.startswith('##') or any(header in line_upper for header in [
                'PATIENT INFORMATION FORM', 'PATIENT INFORMATION',
                'FOR CHILDREN/MINORS ONLY', 'CHILDREN/MINORS',
                'DENTAL BENEFIT PLAN', 'PRIMARY DENTAL PLAN', 'SECONDARY DENTAL PLAN',
                'MEDICAL HISTORY', 'HEALTH HISTORY', 
                'SIGNATURE', 'CONSENT'
            ]):
                # More precise section mapping
                if 'PATIENT INFORMATION' in line_upper:
                    current_section = "Patient Information Form"
                elif 'CHILDREN' in line_upper or 'MINOR' in line_upper:
                    current_section = "FOR CHILDREN/MINORS ONLY"
                elif 'SECONDARY DENTAL' in line_upper:
                    current_section = "Secondary Dental Plan"
                elif 'PRIMARY DENTAL' in line_upper or 'DENTAL BENEFIT' in line_upper:
                    current_section = "Primary Dental Plan"
                elif 'MEDICAL' in line_upper or 'HEALTH' in line_upper:
                    current_section = "Medical History"
                elif 'SIGNATURE' in line_upper or 'CONSENT' in line_upper:
                    current_section = "Signature"
                
                print(f"Section detected: {current_section} from line: {line}")
                i += 1
                continue

            # Handle standalone single-word fields (like "SSN", "Sex")
            standalone_fields = {
                'SSN': ('ssn', 'Social Security No.', 'input', {'input_type': 'ssn', 'hint': None}),
                'Sex': ('sex', 'Sex', 'radio', {'options': [{"name": "Male", "value": "male"}, {"name": "Female", "value": "female"}], 'hint': None}),
                'Social Security No.': ('ssn_2', 'Social Security No.', 'input', {'input_type': 'ssn', 'hint': None}),
                "Today 's Date": ('todays_date', "Today's Date", 'date', {'input_type': 'any', 'hint': None}),
                'Today\'s Date': ('todays_date', 'Today\'s Date', 'date', {'input_type': 'any', 'hint': None}), 
                'Date of Birth': ('date_of_birth', 'Date of Birth', 'date', {'input_type': 'past', 'hint': None}),
                'Birthdate': ('birthdate', 'Birthdate', 'date', {'input_type': 'past', 'hint': None}),
                'Marital Status': ('marital_status', 'Marital Status', 'radio', {
                    'options': [
                        {"name": "Married", "value": "Married"},
                        {"name": "Single", "value": "Single"},
                        {"name": "Divorced", "value": "Divorced"},
                        {"name": "Separated", "value": "Separated"},
                        {"name": "Widowed", "value": "Widowed"}
                    ], 'hint': None
                }),
                'What Is Your Preferred Method Of Contact': ('what_is_your_preferred_method_of_contact', 'What Is Your Preferred Method Of Contact', 'radio', {
                    'options': [
                        {"name": "Mobile Phone", "value": "Mobile Phone"},
                        {"name": "Home Phone", "value": "Home Phone"},
                        {"name": "Work Phone", "value": "Work Phone"},
                        {"name": "E-mail", "value": "E-mail"}
                    ], 'hint': None
                }),
                'Is the Patient a Minor?': ('is_the_patient_a_minor', 'Is the Patient a Minor?', 'radio', {
                    'options': [{"name": "Yes", "value": True}, {"name": "No", "value": False}], 'hint': None
                }),
                'Full-time Student': ('full_time_student', 'Full-time Student', 'radio', {
                    'options': [{"name": "Yes", "value": True}, {"name": "No", "value": False}], 'hint': None
                }),
                'Relationship To Patient': ('relationship_to_patient_2', 'Relationship To Patient', 'radio', {
                    'options': [
                        {"name": "Self", "value": "Self"},
                        {"name": "Spouse", "value": "Spouse"},
                        {"name": "Parent", "value": "Parent"},
                        {"name": "Other", "value": "Other"}
                    ], 'hint': None
                }),
                'If Patient Is A Minor, Primary Residence': ('if_patient_is_a_minor_primary_residence', 'If Patient Is A Minor, Primary Residence', 'radio', {
                    'options': [
                        {"name": "Both Parents", "value": "Both Parents"},
                        {"name": "Mom", "value": "Mom"},
                        {"name": "Dad", "value": "Dad"},
                        {"name": "Step Parent", "value": "Step Parent"},
                        {"name": "Shared Custody", "value": "Shared Custody"},
                        {"name": "Guardian", "value": "Guardian"}
                    ], 'hint': None
                }),
            }
            
            line_stripped = line.strip()
            if line_stripped in standalone_fields:
                base_key, title, field_type, control = standalone_fields[line_stripped]
                
                # Handle field numbering for duplicates
                if base_key in field_counters:
                    field_counters[base_key] += 1
                    key = f"{base_key}_{field_counters[base_key]}"
                else:
                    field_counters[base_key] = 1
                    key = base_key
                
                field = FieldInfo(
                    key=key,
                    title=title,
                    field_type=field_type,
                    section=current_section,
                    control=control,
                    line_idx=i
                )
                fields.append(field)
                i += 1
                continue
            
            # Handle consent paragraphs with Risks/Side Effects
            if (current_section in ["Signature", "Consent"] and 
                len(line) > 50 and 
                any(keyword in line.lower() for keyword in ['risks', 'side effects', 'complications', 'potential'])):
                
                # Collect the consent paragraph
                consent_lines = [line]
                j = i + 1
                while j < len(text_lines) and len(text_lines[j]) > 30:
                    consent_lines.append(text_lines[j])
                    j += 1
                
                # Create consent block with acknowledgment
                consent_fields = self.emit_consent_block("Risks and Acknowledgment", consent_lines, current_section, i)
                fields.extend(consent_fields)
                i = j
                continue
            
            # Handle large text blocks (like terms and conditions)
            # But exclude consent questions with YES/NO patterns
            normalized_line = re.sub(r'[\uf031\uf020\u2003\u2002\u2000-\u200b\ufeff]+', ' ', line)
            has_yes_no_pattern = bool(re.search(r'YES\s+N\s*O?\s*\(Check One\)', normalized_line, re.IGNORECASE))
            
            if (len(line) > 100 and 
                any(keyword in line.lower() for keyword in ['responsibility', 'payment', 'benefit', 'authorize', 'consent']) and
                current_section == "Signature" and
                not has_yes_no_pattern):  # Exclude consent questions
                
                # Collect multi-line text block
                text_content = [line]
                j = i + 1
                
                # Look ahead to collect the full text block
                while j < len(text_lines):
                    next_line = text_lines[j].strip()
                    # Stop if we hit a clear field or section boundary
                    if (len(next_line) < 10 or 
                        next_line.startswith('##') or
                        re.search(r'[A-Za-z][A-Za-z\s]{1,30}_{3,}', next_line) or
                        'initial' in next_line.lower() and len(next_line) < 50):
                        break
                    if len(next_line) > 30:  # Only add substantial content
                        text_content.append(next_line)
                    j += 1
                
                # Create text field
                full_text = ' '.join(text_content)
                
                # Format the text as HTML with proper paragraph breaks
                html_text = self.format_text_as_html(full_text)
                
                # Split into separate text blocks if very long
                if len(full_text) > 1000:
                    # Split at major section breaks
                    split_points = []
                    for pattern in ['Dental Benefit Plans:', 'Scheduling of Appointments:', 'Authorizations:']:
                        pos = full_text.find(pattern)
                        if pos > 0:
                            split_points.append(pos)
                    
                    if split_points:
                        split_points.sort()
                        split_points = [0] + split_points + [len(full_text)]
                        
                        for k in range(len(split_points) - 1):
                            start = split_points[k]
                            end = split_points[k + 1]
                            section_text = full_text[start:end].strip()
                            
                            if section_text:
                                text_key = f"text_{len([f for f in fields if f.field_type == 'text']) + 1}"
                                section_html = self.format_text_as_html(section_text)
                                
                                field = FieldInfo(
                                    key=text_key,
                                    title="",
                                    field_type='text',
                                    section=current_section,
                                    optional=False,
                                    control={
                                        'html_text': section_html,
                                        'temporary_html_text': section_html,
                                        'text': ""
                                    }
                                )
                                fields.append(field)
                    else:
                        # Fallback: create single text block
                        text_key = f"text_{len([f for f in fields if f.field_type == 'text']) + 1}"
                        
                        field = FieldInfo(
                            key=text_key,
                            title="",
                            field_type='text',
                            section=current_section,
                            optional=False,
                            control={
                                'html_text': html_text,
                                'temporary_html_text': html_text,
                                'text': ""
                            }
                        )
                        fields.append(field)
                else:
                    text_key = f"text_{len([f for f in fields if f.field_type == 'text']) + 1}"
                    
                    field = FieldInfo(
                        key=text_key,
                        title="",
                        field_type='text',
                        section=current_section,
                        optional=False,
                        control={
                            'html_text': html_text,
                            'temporary_html_text': html_text,
                            'text': ""
                        }
                    )
                    fields.append(field)
                
                i = j
                continue
            
            # Handle signature fields with initials - improved pattern matching
            if '(initial)' in line.lower() or re.search(r'_{3,}\s*\(initial\)', line, re.IGNORECASE):
                # Extract the text before (initial)
                text_part = re.split(r'\s*_{3,}\s*\(initial\)', line, flags=re.IGNORECASE)[0].strip()
                if text_part:
                    # Create the text field
                    text_key = f"text_{len([f for f in fields if f.field_type == 'text']) + 1}"
                    field = FieldInfo(
                        key=text_key,
                        title="",
                        field_type='text',
                        section=current_section,
                        optional=False,
                        control={
                            'html_text': f"<p>{text_part}</p>",
                            'temporary_html_text': f"<p>{text_part}</p>",
                            'text': ""
                        },
                        line_idx=i
                    )
                    fields.append(field)
                    
                    # Create the initial field
                    if 'initials' in field_counters:
                        field_counters['initials'] += 1
                        initials_key = f"initials_{field_counters['initials']}"
                    else:
                        field_counters['initials'] = 1
                        initials_key = "initials"
                    
                    field = FieldInfo(
                        key=initials_key,
                        title="Initials",
                        field_type='initials',
                        section=current_section,
                        optional=False,
                        control={},
                        line_idx=i
                    )
                    fields.append(field)
                i += 1
                continue
            

            # Handle consent questions with YES/NO checkboxes - improved pattern for both formats
            # First normalize special Unicode spaces that may come from OCR
            normalized_line = re.sub(r'[\uf031\uf020\u2003\u2002\u2000-\u200b\ufeff]+', ' ', line)
            
            consent_patterns = [
                r'(.+?)\s+YES\s+N\s*O?\s*\(Check One\)',  # Standard format with flexible N O spacing
                r'(.+?)\.\s+YES\s+N\s*O\s*\(Check One\)',  # Format with period before YES
                r'(.+?)\s+YES\s+N\s+O\s*\(Check One\)',  # Format with space between N and O
                r'(.+?)\s*\.\s*YES\s+N\s+O\s*\(Check One\)',  # Format with period and spaces
                r'(.+?)\s+YES\s+N\s+O\s+\(Check One\)'   # Format with extra spaces
            ]
            
            consent_found = False
            for pattern in consent_patterns:
                if re.search(pattern, normalized_line, re.IGNORECASE):
                    # Extract the question part
                    question_match = re.match(pattern, normalized_line, re.IGNORECASE)
                    if question_match:
                        question = question_match.group(1).strip()
                        # Truncate very long questions for the key
                        if len(question) > 200:
                            question_short = question[:197] + "..."
                        else:
                            question_short = question
                        
                        key = ModentoSchemaValidator.slugify(question_short)
                        
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
                                'hint': None,
                                'text': "",
                                'html_text': f"<p>{question}</p>",
                                'temporary_html_text': f"<p>{question}</p>"
                            }
                        )
                        fields.append(field)
                        
                        # Add initials field
                        if 'initials' in field_counters:
                            field_counters['initials'] += 1
                            initials_key = f"initials_{field_counters['initials']}"
                        else:
                            field_counters['initials'] = 1
                            initials_key = "initials"
                        
                        field = FieldInfo(
                            key=initials_key,
                            title="Initial",
                            field_type='input',
                            section=current_section,
                            control={'input_type': 'initials'}
                        )
                        fields.append(field)
                        consent_found = True
                        break
            
            if consent_found:
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
                        title="Initials",
                        field_type='initials',
                        section=current_section,
                        optional=False,
                        control={},
                        line_idx=i
                    )
                    fields.append(field)
                i += 1
                continue
            
            # Handle signature and date fields - improved pattern
            if re.search(r'Signature\s*_{5,}.*?Date\s*_{3,}', line, re.IGNORECASE):
                # Add signature field
                field = FieldInfo(
                    key="signature",
                    title="Signature",
                    field_type='signature',
                    section=current_section,
                    optional=False,
                    control={'hint': None, 'input_type': 'name'}
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
            
            # Check for Medical History checkbox run bundling
            if current_section == "Medical History" and self.looks_like_first_history_item(line):
                options, j = self.collect_checkbox_run(text_lines, i)
                if len(options) >= 4:   # threshold to avoid noise
                    field = FieldInfo(
                        key="medical_history",
                        title="Medical History",
                        field_type="checkbox",
                        section=current_section,
                        optional=True,
                        control={"options": options},
                        line_idx=i
                    )
                    fields.append(field)
                    i = j
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
                
                # Better section detection using field content and current section context
                detected_section = self.detect_section(field_name, text_lines[max(0, i-10):i+10], current_section)
                
                # Special handling for work address fields
                context_lines_text = ' '.join(text_lines[max(0, i-3):i+3]).lower()
                if 'work address:' in context_lines_text and field_name.lower() in ['street', 'city', 'state', 'zip']:
                    detected_section = "Patient Information Form"  # Work address is part of patient info
                
                # Create control based on type
                control = {}
                if field_type == 'input':
                    input_type = self.detect_input_type(field_name)
                    control['input_type'] = input_type
                    if input_type == 'phone':
                        control['phone_prefix'] = '+1'
                    
                    # Add hints for specific contexts with better detection
                    hint = None
                    context_check = ' '.join(text_lines[max(0, i-5):i+5]).lower()
                    
                    if 'if different from patient' in full_line.lower():
                        hint = 'If different from patient'
                    elif 'if different from above' in full_line.lower():
                        hint = '(if different from above)'
                    elif 'insurance company' in context_check and field_name.lower() in ['phone', 'street', 'city', 'zip']:
                        hint = 'Insurance Company'
                    elif 'responsible party' in context_check and field_name.lower() in ['first name', 'last name']:
                        hint = 'Name of Responsible Party'
                    elif 'responsible party' in context_check and 'date of birth' in field_name.lower():
                        hint = 'Responsible Party'
                    
                    control['hint'] = hint
                    # Set the input type (including initials)
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
                    control = {'hint': control.get('hint'), 'input_type': 'name'}
                
                # Create unique key with numbering for duplicates with better context awareness
                base_key = ModentoSchemaValidator.slugify(field_name)
                
                # Special case for Middle Initial to use "mi" key 
                if field_name.lower() == "middle initial":
                    base_key = "mi"
                
                # Context-aware field numbering
                context_lines_text = ' '.join(text_lines[max(0, i-5):i+5]).lower()
                existing_fields_in_section = [f for f in fields if f.section == detected_section]
                same_type_in_section = [f for f in existing_fields_in_section if f.key.startswith(base_key)]
                
                # Determine if this should be numbered based on context
                should_number = False
                
                # Check for work address context
                if 'work address' in context_lines_text and field_name.lower() in ['street', 'city', 'state', 'zip']:
                    should_number = True
                
                # Check for secondary dental plan
                elif detected_section == "Secondary Dental Plan" and any(existing_field.key == base_key for existing_field in fields):
                    should_number = True
                
                # Check for children/minors section address variations  
                elif (detected_section == "FOR CHILDREN/MINORS ONLY" and 
                      field_name.lower() in ['street', 'city', 'state', 'zip'] and
                      'if different' in context_lines_text):
                    should_number = True
                
                # Check for insurance company address fields in dental plans
                elif (detected_section in ["Primary Dental Plan", "Secondary Dental Plan"] and
                      field_name.lower() in ['street', 'city', 'state', 'zip'] and
                      any(existing_field.key == base_key for existing_field in fields)):
                    should_number = True
                
                # Check for any duplicate in same section
                elif same_type_in_section:
                    should_number = True
                
                if should_number:
                    if base_key not in field_counters:
                        field_counters[base_key] = len([f for f in fields if f.key.startswith(base_key)])
                    field_counters[base_key] += 1
                    key = f"{base_key}_{field_counters[base_key]}"
                else:
                    if base_key not in field_counters:
                        field_counters[base_key] = 1
                    key = base_key
                
                # Create field with improved required detection
                is_required = self.is_field_required(field_name, detected_section, full_line)
                
                field = FieldInfo(
                    key=key,
                    title=field_name,
                    field_type=field_type,
                    section=detected_section,
                    optional=not is_required,
                    control=control
                )
                fields.append(field)
            
            i += 1
        
        # Post-process fields to fix specific extraction issues
        fields = self.post_process_fields(fields)
        
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
        
        # Sort fields by line_idx to preserve document order, not by section name
        fields.sort(key=lambda f: getattr(f, 'line_idx', 0))
        
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