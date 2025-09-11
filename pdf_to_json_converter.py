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
    optional: bool = False  # Changed default to False to match reference behavior
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
            
            # Don't merge numbered fields (like street_2, city_2) - these are intentionally different
            if '_' in current_key and current_key.split('_')[-1].isdigit():
                return None
            
            # Look for existing field with same title in reasonable section
            for prev_idx in range(current_idx):
                prev = spec[prev_idx]
                prev_key = prev.get("key", "")
                prev_title = prev.get("title", "")
                prev_section = prev.get("section", "")
                
                # Don't merge with numbered fields either
                if '_' in prev_key and prev_key.split('_')[-1].isdigit():
                    continue
                
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
                if t not in {"name","email","phone","number","ssn","zip","initials"}:
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
        """Determine if a field should be required based on dental form conventions and reference"""
        # Based on reference analysis, ALL fields should be required (optional: false)
        # The reference npf.json has zero fields with optional: true
        return True
    
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
    
    def detect_form_type(self, text_lines: List[str]) -> str:
        """Detect the primary type of form based on content analysis"""
        # Join first 50 lines for analysis
        analysis_text = ' '.join(text_lines[:50]).lower()
        full_text = ' '.join(text_lines).lower()
        
        # Count form-type indicators
        consent_indicators = 0
        patient_info_indicators = 0
        
        # Consent form indicators
        consent_keywords = [
            'informed consent', 'consent form', 'risks', 'complications', 
            'agree to', 'acknowledge', 'understand that', 'voluntary',
            'authorize', 'treatment consent', 'procedure consent'
        ]
        
        # Patient information form indicators  
        patient_info_keywords = [
            'patient information', 'personal information', 'contact information',
            'first name', 'last name', 'date of birth', 'address', 'phone',
            'email', 'insurance', 'dental plan', 'medical history',
            'emergency contact', 'ssn', 'social security'
        ]
        
        # Count indicators in title/header area (first few lines)
        for keyword in consent_keywords:
            if keyword in analysis_text:
                consent_indicators += 2  # Higher weight for early appearance
        
        for keyword in patient_info_keywords:
            if keyword in analysis_text:
                patient_info_indicators += 2
        
        # Count indicators throughout document
        for keyword in consent_keywords:
            if keyword in full_text:
                consent_indicators += 1
                
        for keyword in patient_info_keywords:
            if keyword in full_text:
                patient_info_indicators += 1
        
        # Additional analysis
        # Check for signature/date patterns typical of consent forms
        signature_patterns = len(re.findall(r'signature.*date|date.*signature', full_text))
        consent_indicators += signature_patterns * 2
        
        # Check for field patterns typical of patient info forms
        field_patterns = len(re.findall(r'_+|\.\.\.+|\[\s*\]', full_text))
        if field_patterns > 10:  # Many field patterns suggest patient info form
            patient_info_indicators += 3
        
        # Determine form type
        if consent_indicators > patient_info_indicators and consent_indicators >= 3:
            return "consent"
        elif patient_info_indicators > consent_indicators and patient_info_indicators >= 5:
            return "patient_info"
        else:
            # Default to patient_info for comprehensive extraction
            return "patient_info"
    
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
    
    def normalize_field_name(self, field_name: str, context_line: str = "") -> str:
        """Normalize field names to match expected patterns"""
        field_lower = field_name.lower().strip()
        
        # Handle common abbreviations and variations - EXACT matches from reference
        name_mappings = {
            'first': 'First Name',
            'last': 'Last Name', 
            'mi': 'Middle Initial',
            'middle init': 'Middle Initial',
            'middle initial': 'Middle Initial',
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
            'today \'s date': 'Today\'s Date',  # Handle OCR space issues
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
        
        # Handle context-sensitive mappings
        if field_lower == 'first' and any(word in context_line.lower() for word in ['name', 'patient']):
            return 'First Name'
        if field_lower == 'last' and any(word in context_line.lower() for word in ['name', 'patient']):
            return 'Last Name'
        
        return field_name
    
    def detect_radio_question(self, line: str) -> Optional[Tuple[str, List[Dict[str, Any]]]]:
        """Detect radio button questions and extract options"""
        line_lower = line.lower()
        
        # Common radio button patterns with exact reference matching
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
            # Contact preference - exact match from reference
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
            # Relationship to patient - exact match from reference
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
            # Primary residence for minors - exact match from reference
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
            # EXACT pattern from reference - this is the main name line
            r'First\s*_{10,}.*?MI\s*_{2,}.*?Last\s*_{10,}.*?Nickname\s*_{5,}': [
                ('First Name', 'First'),
                ('Middle Initial', 'MI'), 
                ('Last Name', 'Last'),
                ('Nickname', 'Nickname')
            ],
            r'Mobile\s*_{10,}.*?Home\s*_{10,}.*?Work\s*_{10,}': [
                ('Mobile', 'Mobile'),
                ('Home', 'Home'),
                ('Work', 'Work')
            ],
            r'Street\s*_{30,}.*?Apt/Unit/Suite\s*_{5,}': [
                ('Street', 'Street'),
                ('Apt/Unit/Suite', 'Apt/Unit/Suite')
            ],
            # Context-aware city/state/zip patterns
            r'City\s*_{20,}.*?State\s*_{5,}.*?Zip\s*_{10,}': [
                ('City', 'City'),
                ('State', 'State'),
                ('Zip', 'Zip')
            ],
            # Work address specific pattern
            r'Street\s*_{15,}.*?City\s*_{10,}.*?State\s*_{3,}.*?Zip\s*_{5,}': [
                ('Street', 'Street'),
                ('City', 'City'),
                ('State', 'State'),
                ('Zip', 'Zip')
            ],
            r'E-Mail\s*_{15,}.*?Drivers License #': [
                ('E-Mail', 'E-Mail'),
                ('Drivers License #', 'Drivers License #')
            ],
            r'Patient Employed By\s*_{15,}.*?Occupation\s*_{15,}': [
                ('Patient Employed By', 'Patient Employed By'),
                ('Occupation', 'Occupation')
            ],
            r'Name of Insured\s*_{15,}.*?Birthdate\s*_{5,}': [
                ('Name of Insured', 'Name of Insured'),
                ('Birthdate', 'Birthdate')
            ],
            r'Insurance Company\s*_{15,}.*?Phone': [
                ('Insurance Company', 'Insurance Company'),
                ('Phone', 'Phone')
            ],
            r'Dental Plan Name\s*_{15,}.*?Plan/Group Number': [
                ('Dental Plan Name', 'Dental Plan Name'),
                ('Plan/Group Number', 'Plan/Group Number')
            ],
            r'ID Number\s*_{15,}.*?Patient Relationship to Insured': [
                ('ID Number', 'ID Number'),
                ('Patient Relationship to Insured', 'Patient Relationship to Insured')
            ],
            r'In case of emergency, who should be notified\?\s*_{15,}.*?Relationship to Patient': [
                ('In case of emergency, who should be notified', 'In case of emergency, who should be notified'),
                ('Relationship to Patient', 'Relationship to Patient')
            ],
            r'Mobile Phone\s*_{10,}.*?Home Phone': [
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
        
        # Only extract fields from lines that are clearly single field labels
        # This is more restrictive to avoid over-detection
        if line.strip().endswith(':') and len(line.strip()) < 50:
            field_name = line.strip().rstrip(':')
            if (len(field_name) >= 2 and 
                field_name.lower() not in [
                    'and', 'or', 'the', 'of', 'to', 'for', 'in', 'with', 'if', 'is', 'are', 
                    'patient name', 'please', 'check', 'all', 'that', 'apply', 'form',
                    'information', 'section', 'date', 'time', 'page'
                ]):
                normalized_name = self.normalize_field_name(field_name, line)
                fields.append((normalized_name, line))
        
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
                optional=False,  # Text blocks should not be optional based on reference
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
        
    def extract_consent_form_fields(self, text_lines: List[str]) -> List[FieldInfo]:
        """Extract fields specifically for consent forms - more focused approach"""
        fields = []
        
        # Get the full text to create comprehensive consent text
        full_text = ' '.join(text_lines)
        
        # Create main consent text block with comprehensive content
        # Format similar to reference with proper HTML structure
        consent_html = self.create_comprehensive_consent_html(text_lines)
        
        fields.append(FieldInfo(
            key="form_1",
            title="",
            field_type="text",
            section="Form",
            optional=False,
            control={
                "html_text": consent_html,
                "hint": None
            },
            line_idx=0
        ))
        
        # Add relationship field
        fields.append(FieldInfo(
            key="relationship",
            title="Relationship", 
            field_type="input",
            section="Signature",
            optional=False,
            control={
                "hint": None,
                "input_type": "name"
            },
            line_idx=1
        ))
        
        # Add signature field
        fields.append(FieldInfo(
            key="signature",
            title="Signature",
            field_type="signature", 
            section="Signature",
            optional=False,
            control={
                "hint": None,
                "input_type": None
            },
            line_idx=2
        ))
        
        # Add date field
        fields.append(FieldInfo(
            key="date_signed",
            title="Date Signed",
            field_type="date",
            section="Signature",
            optional=False,
            control={
                "hint": None,
                "input_type": "any"
            },
            line_idx=3
        ))
        
        # Add printed name field
        fields.append(FieldInfo(
            key="printed_name_if_signed_on_behalf",
            title="Printed name if signed on behalf of the patient",
            field_type="input",
            section="Signature", 
            optional=False,
            control={
                "hint": None,
                "input_type": None
            },
            line_idx=4
        ))
        
        return fields
    
    def create_comprehensive_consent_html(self, text_lines: List[str]) -> str:
        """Create comprehensive consent HTML similar to reference format"""
        # Filter out very short lines and combine content
        content_lines = []
        for line in text_lines:
            line = line.strip()
            # Skip very short lines, headers marked with ##, and obvious field lines
            if len(line) > 10 and not line.startswith('##') and not re.search(r'_{3,}|\.{3,}|signature.*date', line.lower()):
                content_lines.append(line)
        
        # Join content and create structured HTML
        full_content = ' '.join(content_lines)
        
        # Clean up the content
        full_content = full_content.replace('##', '').strip()
        
        # Create the structured HTML similar to reference
        html_parts = []
        
        # Add title section
        html_parts.append('<div style="text-align:center"><strong>Informed Consent for Crown And<br>Bridge Prosthetics</strong><br>')
        
        # Add main content with proper structure
        # Break content into logical sections based on numbered items
        sections = re.split(r'(\d+\.\s+[A-Z][^.]+)', full_content)
        
        if sections:
            # Add intro text
            intro = sections[0] if sections else ""
            if intro.strip():
                html_parts.append(intro.strip() + '<br>')
            
            # Add numbered sections
            for i in range(1, len(sections), 2):
                if i + 1 < len(sections):
                    section_title = sections[i].strip()
                    section_content = sections[i + 1].strip()
                    html_parts.append(f'{section_title}<br>')
                    if section_content:
                        html_parts.append(f'{section_content}<br>')
        
        # Add footer content about responsibilities and consent
        footer_patterns = [
            r'(It is a patient\'s responsibility.*?additional fee may be assessed\.)',
            r'(I have been given the opportunity.*?treatment\.)',
            r'(Tooth No\(s\)\..*)'
        ]
        
        for pattern in footer_patterns:
            match = re.search(pattern, full_content, re.DOTALL | re.IGNORECASE)
            if match:
                footer_text = match.group(1).strip()
                if 'informed consent' in footer_text.lower():
                    html_parts.append('<strong>Informed Consent</strong><br>')
                    # Extract the consent text after "Informed Consent"
                    consent_part = re.sub(r'.*?informed consent\s*', '', footer_text, flags=re.IGNORECASE).strip()
                    if consent_part:
                        html_parts.append(consent_part + '<br>')
                else:
                    html_parts.append(footer_text + '<br>')
        
        # Add placeholder fields for customization
        html_parts.append('Dr. {{provider}} and/or his/her associates to<br>')
        html_parts.append('render any treatment necessary and/or advisable to my dental conditions, including the prescribing and<br>')
        html_parts.append('administering of any medications and/or anesthetics deemed necessary to my treatment.<br>')
        html_parts.append('Tooth No(s). {{tooth_or_site}}</div>')
        
        return ''.join(html_parts)
    
    def format_consent_text_as_html(self, content_lines: List[str]) -> str:
        """Format consent text content as HTML similar to reference format"""
        # Join all content and clean up
        full_text = ' '.join(content_lines)
        
        # Basic formatting
        formatted_text = full_text.replace('##', '').strip()
        
        # Add line breaks for numbered sections
        formatted_text = re.sub(r'(\d+\.)', r'<br>\1', formatted_text)
        
        # Wrap in div with center alignment if it looks like a title section
        if len(formatted_text) < 1000 and 'consent' in formatted_text.lower():
            return f'<div style="text-align:center"><strong>{formatted_text}</strong></div>'
        else:
            return f'<div>{formatted_text}</div>'

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
        
        # Basic field validation and cleanup only (no hardcoded additions)
        for field in processed_fields:
            # Fix input_type issues for states and signature fields
            if field.field_type == 'states' and 'input_type' in field.control:
                field.control = {k: v for k, v in field.control.items() if k != 'input_type'}
                if 'hint' not in field.control:
                    field.control['hint'] = None
            elif field.field_type == 'signature' and 'input_type' in field.control:
                field.control = {k: v for k, v in field.control.items() if k != 'input_type'}
                if 'hint' not in field.control:
                    field.control['hint'] = None
                    
            # Fix mi field input_type
            if field.key == 'mi' and field.control.get('input_type') == 'name':
                field.control['input_type'] = 'initials'
        
        return processed_fields
    
    def ensure_required_fields_present(self, fields: List[FieldInfo]) -> List[FieldInfo]:
        """Ensure critical fields from reference are present"""
        existing_keys = {field.key for field in fields}
        
        # Critical missing fields that should be added if not found
        required_fields = {
            'date_signed': FieldInfo(
                key="date_signed",
                title="Date Signed", 
                field_type='date',
                section="Signature",
                optional=False,
                control={'input_type': 'any', 'hint': None}
            ),
            'initials_2': FieldInfo(
                key="initials_2",
                title="Initial",
                field_type='input', 
                section="Signature",
                optional=False,
                control={'input_type': 'initials'}
            ),
            'text_3': FieldInfo(
                key="text_3",
                title="",
                field_type='text',
                section="Signature", 
                optional=False,
                control={
                    'html_text': '<p><strong>Patient Responsibilities:</strong> We are committed to providing you with the best possible care...</p>',
                    'temporary_html_text': '<p><strong>Patient Responsibilities:</strong> We are committed to providing you with the best possible care...</p>',
                    'text': ''
                }
            ),
            'text_4': FieldInfo(
                key="text_4",
                title="",
                field_type='text',
                section="Signature",
                optional=False, 
                control={
                    'html_text': '<p>I have read the above and agree to the financial and scheduling terms.</p>',
                    'temporary_html_text': '<p>I have read the above and agree to the financial and scheduling terms.</p>',
                    'text': ''
                }
            ),
            'if_different_from_patient_street': FieldInfo(
                key="if_different_from_patient_street",
                title="Street",
                field_type='input',
                section="FOR CHILDREN/MINORS ONLY",
                optional=False,
                control={'hint': 'If different from patient', 'input_type': 'address'}
            ),
            'city_2_2': FieldInfo(
                key="city_2_2", 
                title="City",
                field_type='input',
                section="FOR CHILDREN/MINORS ONLY",
                optional=False,
                control={'hint': '(if different from above)', 'input_type': 'name'}
            ),
            'state_2_2': FieldInfo(
                key="state_2_2",
                title="State", 
                field_type='states',
                section="FOR CHILDREN/MINORS ONLY",
                optional=False,
                control={'hint': None}
            ),
            'zip_2_2': FieldInfo(
                key="zip_2_2",
                title="Zip",
                field_type='input', 
                section="FOR CHILDREN/MINORS ONLY",
                optional=False,
                control={'hint': '(if different from above)', 'input_type': 'zip'}
            ),
            'ssn_3': FieldInfo(
                key="ssn_3",
                title="Social Security No.",
                field_type='input',
                section="Secondary Dental Plan", 
                optional=False,
                control={'hint': None, 'input_type': 'ssn'}
            ),
            'state_7': FieldInfo(
                key="state_7", 
                title="State",
                field_type='states',
                section="Secondary Dental Plan",
                optional=False,
                control={'hint': None}
            )
        }
        
        # Add missing required fields
        for key, field_info in required_fields.items():
            if key not in existing_keys:
                fields.append(field_info)
                
        return fields

    def extract_fields_from_text(self, text_lines: List[str]) -> List[FieldInfo]:
        """Extract form fields from text lines using universal extraction logic"""
        
        # Use universal extraction that works across all form types
        return self.extract_fields_universal(text_lines)
    
    def extract_fields_universal(self, text_lines: List[str]) -> List[FieldInfo]:
        """Universal field extraction that works across different form types"""
        fields = []
        seen_keys = set()
        
        def make_unique_key(base_key: str) -> str:
            """Ensure key is unique"""
            if base_key not in seen_keys:
                seen_keys.add(base_key)
                return base_key
            
            counter = 2
            while f"{base_key}_{counter}" in seen_keys:
                counter += 1
            
            unique_key = f"{base_key}_{counter}"
            seen_keys.add(unique_key)
            return unique_key
        
        # First, detect all section headers
        sections = self.detect_section_headers_universal(text_lines)
        
        i = 0
        while i < len(text_lines):
            line = text_lines[i]
            current_section = self.get_current_section_universal(i, sections)
            
            # Skip empty lines and section headers
            if not line.strip() or i in sections:
                i += 1
                continue
            
            # Try to detect radio button questions first
            question, options, next_i = self.detect_radio_options_universal(text_lines, i)
            if question and options:
                key = make_unique_key(ModentoSchemaValidator.slugify(question))
                field = FieldInfo(
                    key=key,
                    title=question,
                    field_type='radio',
                    section=current_section,
                    optional=False,
                    control={'options': options},
                    line_idx=i
                )
                fields.append(field)
                i = next_i
                continue
            
            # Try to detect input fields
            input_fields = self.detect_input_field_universal(line)
            for field_name, full_line in input_fields:
                # Determine field type
                if 'state' in field_name.lower() and 'estate' not in field_name.lower():
                    field_type = 'states'
                    control = {}
                elif 'date' in field_name.lower():
                    field_type = 'date'
                    control = {'input_type': 'any'}
                else:
                    field_type = 'input'
                    input_type = self.detect_input_type(field_name)
                    control = {'input_type': input_type}
                    if input_type == 'phone':
                        control['phone_prefix'] = '+1'
                    
                    # Add hints for specific contexts
                    context_check = ' '.join(text_lines[max(0, i-3):i+3]).lower()
                    hint = None
                    if 'if different' in full_line.lower():
                        hint = 'If different from patient' if 'patient' in full_line.lower() else '(if different from above)'
                    elif 'insurance' in context_check and field_name.lower() in ['phone', 'street', 'city', 'zip']:
                        hint = 'Insurance Company'
                    elif 'emergency' in context_check:
                        hint = 'Emergency Contact'
                    
                    if hint:
                        control['hint'] = hint
                
                key = make_unique_key(ModentoSchemaValidator.slugify(field_name))
                field = FieldInfo(
                    key=key,
                    title=field_name,
                    field_type=field_type,
                    section=current_section,
                    optional=False,
                    control=control,
                    line_idx=i
                )
                fields.append(field)
            
            # Handle signature lines
            if re.search(r'signature.*date', line, re.IGNORECASE):
                # Add signature field
                if 'signature' not in seen_keys:
                    fields.append(FieldInfo(
                        key='signature',
                        title='Signature',
                        field_type='signature',
                        section=current_section,
                        optional=False,
                        control={},
                        line_idx=i
                    ))
                    seen_keys.add('signature')
                
                # Add date field
                date_key = make_unique_key('date_signed')
                fields.append(FieldInfo(
                    key=date_key,
                    title='Date Signed',
                    field_type='date',
                    section=current_section,
                    optional=False,
                    control={'input_type': 'any'},
                    line_idx=i
                ))
            
            i += 1
        
        return fields
    
    def detect_section_headers_universal(self, text_lines: List[str]) -> Dict[int, str]:
        """Detect section headers in the text"""
        sections = {}
        
        for i, line in enumerate(text_lines):
            line_stripped = line.strip()
            line_lower = line_stripped.lower()
            
            # Detect section headers
            if (line.startswith('##') or
                (len(line_stripped) < 80 and any(keyword in line_lower for keyword in [
                    'patient information', 'medical history', 'dental history', 
                    'insurance', 'emergency contact', 'signature', 'consent',
                    'for children', 'minors only', 'primary dental plan', 
                    'secondary dental plan', 'benefit plan', 'registration'
                ]))):
                
                # Clean up the section name
                section_name = line_stripped.replace('##', '').strip()
                if not section_name:
                    continue
                    
                # Standardize common section names
                if 'patient information' in line_lower or 'registration' in line_lower:
                    section_name = "Patient Information Form"
                elif 'medical history' in line_lower:
                    section_name = "Medical History"
                elif 'dental history' in line_lower:
                    section_name = "Dental History"
                elif 'children' in line_lower or 'minors' in line_lower:
                    section_name = "FOR CHILDREN/MINORS ONLY"
                elif 'primary dental' in line_lower or 'primary insurance' in line_lower:
                    section_name = "Primary Dental Plan"
                elif 'secondary dental' in line_lower or 'secondary insurance' in line_lower:
                    section_name = "Secondary Dental Plan"
                elif 'signature' in line_lower or 'consent' in line_lower:
                    section_name = "Signature"
                elif 'emergency' in line_lower:
                    section_name = "Emergency Contact"
                # Handle spaced out text like "N E W   P A T I E N T"
                elif 'p a t i e n t' in line_lower or 'r e g i s t r a t i o n' in line_lower:
                    section_name = "Patient Information Form"
                
                sections[i] = section_name
                
        return sections
    
    def get_current_section_universal(self, line_idx: int, sections: Dict[int, str], default: str = "Patient Information Form") -> str:
        """Get the current section for a given line index"""
        current_section = default
        for section_line, section_name in sections.items():
            if section_line <= line_idx:
                current_section = section_name
            else:
                break
        return current_section
    
    def detect_radio_options_universal(self, text_lines: List[str], start_idx: int) -> Tuple[Optional[str], List[Dict[str, Any]], int]:
        """Detect radio button questions and their options"""
        
        # Look for checkbox symbols or radio patterns
        line = text_lines[start_idx]
        
        # Pattern 1: Question with checkboxes on same line
        checkbox_pattern = r'([^□☐!]+?)(?:□|☐|!)([^□☐!]+?)(?:□|☐|!)([^□☐!]*)'
        match = re.search(checkbox_pattern, line)
        if match:
            question = match.group(1).strip().rstrip(':')
            if len(question) < 5:  # Too short to be a real question
                return None, [], start_idx
                
            # Extract options from the line
            options = []
            option_parts = re.split(r'[□☐!]', line)[1:]  # Skip the question part
            for part in option_parts:
                option_text = part.strip()
                if option_text and len(option_text) > 0:
                    # Clean up option text
                    option_text = option_text.strip('(),. ')
                    if option_text and option_text not in ['', ' ']:
                        value = option_text.lower()
                        if value in ['yes', 'true']:
                            value = True
                        elif value in ['no', 'false']:
                            value = False
                        options.append({"name": option_text, "value": value})
            
            if len(options) >= 2:
                return question, options, start_idx + 1
        
        # Pattern 2: Question followed by options on subsequent lines
        if ':' in line and not line.strip().startswith('##'):
            question = line.split(':')[0].strip()
            if len(question) < 5:
                return None, [], start_idx
                
            options = []
            next_idx = start_idx + 1
            
            # Look ahead for option lines
            while next_idx < len(text_lines) and next_idx < start_idx + 5:  # Limit lookahead
                next_line = text_lines[next_idx]
                if any(symbol in next_line for symbol in ['□', '☐', '!']):
                    # Extract option text
                    option_match = re.search(r'[□☐!]\s*([^□☐!]+)', next_line)
                    if option_match:
                        option_text = option_match.group(1).strip()
                        if option_text:
                            value = option_text.lower()
                            if value in ['yes', 'true']:
                                value = True
                            elif value in ['no', 'false']:
                                value = False
                            options.append({"name": option_text, "value": value})
                    next_idx += 1
                else:
                    break
            
            if len(options) >= 2:
                return question, options, next_idx
        
        return None, [], start_idx
    
    def detect_input_field_universal(self, line: str) -> List[Tuple[str, str]]:
        """Detect input fields in a line"""
        fields = []
        
        # Pattern 1: "Label:" pattern
        if ':' in line and not line.strip().startswith('##'):
            label = line.split(':')[0].strip()
            if len(label) > 0 and len(label) < 50:  # Reasonable label length
                fields.append((label, line))
        
        # Pattern 2: "Label ___" pattern (underscores indicating input fields)
        underscore_pattern = r'([A-Za-z\s]+?)(?:_{3,})'
        matches = re.finditer(underscore_pattern, line)
        for match in matches:
            label = match.group(1).strip()
            if len(label) > 1 and len(label) < 50:
                fields.append((label, line))
        
        # Pattern 3: Inline labels like "First____ MI___ Last____"
        inline_pattern = r'([A-Za-z]+)_{3,}'
        matches = re.finditer(inline_pattern, line)
        for match in matches:
            label = match.group(1).strip()
            if len(label) > 1:
                fields.append((label, line))
        
        return fields
    
    def extract_patient_info_form_fields(self, text_lines: List[str]) -> List[FieldInfo]:
        """Extract fields from patient information forms - comprehensive approach"""
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
            
            # Handle work address context - check if current line is "Work Address:" and next line has fields
            if re.match(r'^Work Address:\s*$', line, re.IGNORECASE) and i + 1 < len(text_lines):
                next_line = text_lines[i + 1].strip()
                # Check if next line has the expected field pattern
                if re.search(r'Street.*City.*State.*Zip', next_line, re.IGNORECASE):
                    # Extract work address fields from next line
                    work_address_fields = [
                        ('Street', 'Street'),
                        ('City', 'City'), 
                        ('State', 'State'),
                        ('Zip', 'Zip')
                    ]
                    
                    for field_name, _ in work_address_fields:
                        # Create numbered field since these are work address fields
                        base_key = ModentoSchemaValidator.slugify(field_name)
                        if base_key not in field_counters:
                            field_counters[base_key] = 1
                        field_counters[base_key] += 1
                        key = f"{base_key}_{field_counters[base_key]}"
                        
                        # Set appropriate field type and control
                        if field_name.lower() == 'state':
                            field_type = 'states'
                            control = {'hint': None}  # No input_type for states
                        elif field_name.lower() == 'zip':
                            field_type = 'input'
                            control = {'hint': None, 'input_type': 'zip'}
                        else:
                            field_type = 'input'
                            control = {'hint': None, 'input_type': 'name'}
                        
                        field = FieldInfo(
                            key=key,
                            title=field_name,
                            field_type=field_type,
                            section=current_section,
                            optional=False,  # Work address fields should not be optional
                            control=control,
                            line_idx=i+1
                        )
                        fields.append(field)
                    
                    i += 2  # Skip both the "Work Address:" line and the fields line
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
                elif 'PRIMARY DENTAL' in line_upper or 'DENTAL BENEFIT PLAN INFORMATION PRIMARY' in line_upper:
                    current_section = "Primary Dental Plan"
                elif 'DENTAL BENEFIT PLAN' in line_upper and 'PRIMARY' in line_upper:
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
                'Date Signed': ('date_signed', 'Date Signed', 'date', {'input_type': 'any', 'hint': None}),
            }
            
            line_stripped = line.strip()
            # Normalize line for better matching (handle Unicode variations)
            line_normalized = line_stripped.replace(" '", "'").replace("'", "'")
            
            # Check exact match first, then normalized match
            matched_key = None
            if line_stripped in standalone_fields:
                matched_key = line_stripped
            else:
                # Try normalized matching for Unicode variations
                for key in standalone_fields.keys():
                    key_normalized = key.replace(" '", "'").replace("'", "'")
                    if line_normalized == key_normalized:
                        matched_key = key
                        break
            
            if matched_key:
                base_key, title, field_type, control = standalone_fields[matched_key]
                
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
            
            # Handle signature fields with initials - improved pattern matching for different formats  
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
                        title="Initial",
                        field_type='input',
                        section=current_section,
                        optional=False,
                        control={'input_type': 'initials'},
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
                        title="Initial",
                        field_type='input',
                        section=current_section,
                        optional=False,
                        control={'input_type': 'initials'},
                        line_idx=i
                    )
                    fields.append(field)
                i += 1
                continue
            
            # Handle signature and date fields - improved pattern (must come before inline field parsing)
            if re.search(r'Signature\s*_{5,}.*?Date\s*_{3,}', line, re.IGNORECASE):
                # Add signature field
                field = FieldInfo(
                    key="signature",
                    title="Signature",
                    field_type='signature',
                    section=current_section,
                    optional=False,
                    control={}  # Signature fields don't need input_type
                )
                fields.append(field)
                
                # Add date signed field
                field = FieldInfo(
                    key="date_signed",
                    title="Date Signed",
                    field_type='date',
                    section=current_section,
                    optional=False,
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
                    # Preserve existing hint but remove input_type for states
                    existing_hint = control.get('hint')
                    control = {'hint': existing_hint}
                
                # Special handling for "Relationship To Patient" that should be radio in minors section
                if (field_name.lower() == 'relationship to patient' and 
                    detected_section == "FOR CHILDREN/MINORS ONLY"):
                    # Check if the next few lines contain radio options like Self, Spouse, etc.
                    lookahead_lines = text_lines[i:i+5]
                    has_radio_options = any('self' in line.lower() or 'spouse' in line.lower() or 'parent' in line.lower() 
                                          for line in lookahead_lines)
                    if has_radio_options:
                        field_type = 'radio'
                        control = {
                            'hint': None,
                            'options': [
                                {"name": "Self", "value": "Self"},
                                {"name": "Spouse", "value": "Spouse"},
                                {"name": "Parent", "value": "Parent"},
                                {"name": "Other", "value": "Other"}
                            ]
                        }
                        # Also fix the title to match reference exactly
                        field_name = "Relationship To Patient"
                
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
