#!/usr/bin/env python3
"""
Consent Form to Modento JSON Converter

This script extracts consent form fields from PDF and DOCX documents and converts them
to JSON format compliant with the Modento Forms schema specification.

This converter is specifically designed for consent forms and includes all the rules,
formatting, and processing logic required for consent form extraction.

Usage:
    python consent_converter.py <file_path> [--output <output_path>]
    python consent_converter.py <directory> [--output-dir <output_dir>]
"""

import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

# Docling imports for advanced document processing
from docling.document_converter import DocumentConverter, FormatOption
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.datamodel.base_models import InputFormat
from docling.backend.docling_parse_backend import DoclingParseDocumentBackend
from docling.pipeline.standard_pdf_pipeline import StandardPdfPipeline


@dataclass
class FieldInfo:
    """Information about a detected consent form field"""
    key: str
    title: str
    field_type: str
    section: str
    optional: bool = False
    control: Dict[str, Any] = None
    line_idx: int = 0
    
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
        
        for item in spec:
            if 'key' in item:
                item['key'] = make_unique(item['key'])
        
        return spec
    
    @classmethod
    def validate_and_normalize(cls, spec: List[Dict[str, Any]]) -> Tuple[bool, List[str], List[Dict[str, Any]]]:
        """Validate and normalize a Modento spec for consent forms"""
        errors = []
        if not isinstance(spec, list):
            return False, ["Spec must be a top-level JSON array"], spec
        
        # Ensure signature field uniqueness
        sig_idxs = [i for i, q in enumerate(spec) if q.get("type") == "signature"]
        if sig_idxs:
            first = sig_idxs[0]
            spec[first]["key"] = "signature"
            for j in sig_idxs[1:]:
                spec[j]["__drop__"] = True
        spec = [q for q in spec if not q.get("__drop__")]
        if not sig_idxs:
            spec.append({"key":"signature","title":"Signature","section":"Signature","optional":False,"type":"signature","control":{}})
        
        # Ensure unique keys
        spec = cls.ensure_unique_keys(spec)
        
        # Per-question validation
        for q in spec:
            q_type = q.get("type")
            if q_type not in cls.VALID_TYPES:
                errors.append(f"Unknown type '{q_type}' on key '{q.get('key')}'")
                continue
            
            ctrl = q.setdefault("control", {})
            
            # Keep hint as null if explicitly set (for reference parity)
            if 'hint' not in ctrl:
                ctrl['hint'] = None
            
            if q_type == "input":
                t = ctrl.get("input_type")
                if t is None:
                    # Keep it as None if explicitly set
                    ctrl["input_type"] = None
                elif t not in cls.VALID_INPUT_TYPES:
                    ctrl["input_type"] = "name"
            
            if q_type == "date":
                t = ctrl.get("input_type")
                # Allow "any" as a valid date input type for consent forms
                if t not in {"past", "future", "any"}:
                    ctrl["input_type"] = "any"
            
            if q_type == "signature":
                # For signature fields, set hint and input_type to None
                ctrl["hint"] = None
                ctrl["input_type"] = None
        
        return len(errors) == 0, errors, spec


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
    
    def is_consent_content(self, text: str) -> bool:
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
    
    def detect_consent_sections(self, text_lines: List[str]) -> Dict[str, Any]:
        """Detect consent form sections from text lines"""
        sections = {
            'consent_paragraphs': [],
            'signature_section': False,
            'patient_info_section': False,
            'procedure_section': False
        }
        
        for i, line in enumerate(text_lines):
            line_lower = line.lower().strip()
            
            # Detect consent paragraphs
            if self.is_consent_content(line):
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


class HeaderFooterManager:
    """Manages universal header/footer removal for consent documents"""
    
    def __init__(self):
        """Initialize the header/footer manager"""
        # Patterns for practice information that should be removed
        self.practice_patterns = [
            r'www\.\w+\.com',
            r'\w+@\w+\.com',
            r'\(\d{3}\)\s*\d{3}-?\d{4}',
            r'\d+\s+[A-Z][A-Za-z\s]+,\s+[A-Z]{2}\s+\d{5}',
            r'Route\s+\d+.*\d{5}',
            r'Smile@.*\.com',
        ]
        self.compiled_practice_patterns = [re.compile(p, re.IGNORECASE) for p in self.practice_patterns]
    
    def is_practice_information(self, line: str) -> bool:
        """Check if a line contains practice information that should be removed"""
        line_lower = line.lower().strip()
        
        # Check against compiled patterns
        for pattern in self.compiled_practice_patterns:
            if pattern.search(line):
                return True
        
        # Check for specific practice info markers
        practice_markers = [
            'www.', '@', 'route', 'office:', 'phone:', 'fax:'
        ]
        
        return any(marker in line_lower for marker in practice_markers)
    
    def remove_practice_headers_footers(self, text_lines: List[str]) -> List[str]:
        """Remove practice headers/footers from consent forms"""
        cleaned_lines = []
        
        for line in text_lines:
            if not line.strip():
                continue
            
            if not self.is_practice_information(line):
                cleaned_lines.append(line)
        
        return cleaned_lines


class ConsentFormFieldExtractor:
    """Extract form fields from consent PDFs and DOCX documents"""
    
    def __init__(self):
        """Initialize the extractor with Docling"""
        # Setup Docling converter with optimized settings
        pipeline_options = PdfPipelineOptions()
        pipeline_options.do_ocr = True
        pipeline_options.do_table_structure = True
        
        format_option = FormatOption(
            pipeline_options=pipeline_options,
            backend=DoclingParseDocumentBackend,
            pipeline_cls=StandardPdfPipeline
        )
        
        self.converter = DocumentConverter(
            format_options={
                InputFormat.PDF: format_option,
            }
        )
        
        # Initialize managers
        self.consent_shaper = ConsentShapingManager()
        self.header_footer_manager = HeaderFooterManager()
        
        # Try to import python-docx for enhanced DOCX formatting detection
        try:
            import docx
            self.docx_available = True
        except ImportError:
            self.docx_available = False
        
        # Consent-specific field patterns for better extraction
        self.consent_field_patterns = {
            'printed_name': re.compile(r'(?:printed?\\s*name|print\\s*name|name\\s*\\(print\\)|patient\\s*print)', re.IGNORECASE),
            'date_of_birth': re.compile(r'(?:date\\s*of\\s*birth|birth\\s*date|dob|born)', re.IGNORECASE),
            'relationship': re.compile(r'(?:relationship|relation\\s*to|guardian|parent|spouse)', re.IGNORECASE),
            'consent_date': re.compile(r'(?:consent\\s*date|date\\s*of\\s*consent|today)', re.IGNORECASE),
        }
    
    def _detect_bold_lines_from_docx(self, file_path: Path) -> Dict[str, bool]:
        """Detect which text lines are bold in a DOCX file using python-docx
        
        Returns a dictionary mapping line text to whether it's bold
        """
        if not self.docx_available or file_path.suffix.lower() not in ['.docx', '.doc']:
            return {}
        
        try:
            import docx
            doc = docx.Document(str(file_path))
            bold_lines = {}
            
            for para in doc.paragraphs:
                text = para.text.strip()
                if not text:
                    continue
                
                # Check if paragraph has any bold runs
                # A line is considered bold if all non-empty runs are bold
                runs_with_text = [run for run in para.runs if run.text.strip()]
                if runs_with_text:
                    is_bold = all(run.bold for run in runs_with_text if run.text.strip())
                    bold_lines[text] = is_bold
            
            return bold_lines
        except Exception:
            # If there's any error with python-docx processing, just return empty dict
            return {}
    
    def extract_text_from_document(self, file_path: Path) -> Tuple[List[str], Dict[str, Any]]:
        """Extract text from PDF or DOCX document using Docling"""
        
        result = self.converter.convert(str(file_path))
        doc = result.document
        
        # Extract text content
        text_content = doc.export_to_text()
        text_lines = [line.strip() for line in text_content.split('\n') if line.strip()]
        
        # For DOCX files, detect bold formatting
        bold_lines = self._detect_bold_lines_from_docx(file_path)
        
        # Get pipeline information
        pipeline_info = {
            'pipeline': result.input.format.name if result.input else 'Unknown',
            'backend': 'DoclingParseDocumentBackend',
            'document_format': file_path.suffix.upper().lstrip('.'),
            'ocr_used': file_path.suffix.lower() == '.pdf',
            'ocr_engine': 'EasyOCR' if file_path.suffix.lower() == '.pdf' else None,
            'bold_lines': bold_lines  # Pass bold line info for later use
        }
        
        return text_lines, pipeline_info
    
    def extract_consent_form_fields(self, text_lines: List[str], pipeline_info: Optional[Dict[str, Any]] = None) -> List[FieldInfo]:
        """Extract fields specifically for consent forms"""
        
        fields = []
        processed_keys = set()
        current_section = "Form"
        
        # Get bold line information if available
        bold_lines = {}
        if pipeline_info and 'bold_lines' in pipeline_info:
            bold_lines = pipeline_info['bold_lines']
        
        # Clean headers/footers
        text_lines = self.header_footer_manager.remove_practice_headers_footers(text_lines)
        
        # Join all text for pattern analysis
        full_text = '\n'.join(text_lines)
        
        # Provider placeholder detection patterns
        provider_patterns = [
            r'Dr\.\s*__+',
            r'Dr\.\s*\t+',
            r'Dr\.\s*to\s+perform',
            r'consent\s+to\s+Dr\.',
            r'authorize\s+Dr\.',
        ]
        
        # Universal field patterns for consent forms
        # Order matters - more specific patterns first
        field_patterns = [
            (r'Printed?\s+[Nn]ame\s+if\s+signed\s+on\s+behalf', 'printed_name_if_signed_on_behalf', 'Printed name if signed on behalf of the patient', 'input', {'input_type': None, 'hint': None}),
            (r'Patient.*Name.*Print', 'patient_name_print', 'Patient Name (Print)', 'input', {'input_type': 'name', 'hint': None}),
            (r'Relationship\s*_+', 'relationship', 'Relationship', 'input', {'input_type': 'name', 'hint': None}),
            (r'Date\s+of\s+Birth', 'date_of_birth', 'Date of Birth', 'date', {'input_type': 'past', 'hint': None}),
            (r'tooth\s+no(?:mber)?\.?\s*[:\(]?\s*_+', 'tooth_number', 'Tooth Number', 'input', {'input_type': 'name', 'hint': None}),
            (r'procedure.*follows?', 'procedure_description', 'Procedure Description', 'input', {'input_type': 'name', 'hint': None}),
            (r'alternative.*treatment', 'alternative_treatment', 'Alternative Treatment', 'input', {'input_type': 'name', 'hint': None}),
        ]
        
        # EXTRACT MAIN CONSENT TEXT BLOCK
        consent_text_lines = []
        signature_start_idx = None
        
        for i, line in enumerate(text_lines):
            line_lower = line.lower()
            # Look for signature section markers - be more specific to avoid false positives
            if re.search(r'signature\s*:', line_lower) or re.search(r'patient\s+signature', line_lower):
                signature_start_idx = i
                break
            elif line.strip():
                # Include all non-empty lines including headers marked with ##
                consent_text_lines.append(line.strip())
        
        # Variable to hold the detected consent title for section naming
        consent_section_name = "Form"
        
        if consent_text_lines:
            # Create main consent text field with provider placeholders
            # Now returns tuple (html, title)
            consent_html, detected_title = self._create_enhanced_consent_html(consent_text_lines, full_text, provider_patterns, bold_lines)
            
            # Use detected title as section name if available
            if detected_title:
                consent_section_name = detected_title
            
            consent_field = FieldInfo(
                key='form_1',
                title='',
                field_type='text',
                section=consent_section_name,
                optional=False,
                control={'html_text': consent_html},
                line_idx=0
            )
            fields.append(consent_field)
            processed_keys.add('form_1')
        
        # EXTRACT SIGNATURE SECTION FIELDS
        if signature_start_idx is not None:
            current_section = "Signature"
            signature_lines = text_lines[signature_start_idx:]
            
            # Process signature area fields using universal patterns
            for i, line in enumerate(signature_lines):
                line_stripped = line.strip()
                
                # Skip empty lines and headers
                if not line_stripped or line_stripped.startswith('#'):
                    continue
                
                # Skip witness and doctor signature fields
                if self._is_witness_or_doctor_signature_field(line_stripped.lower()):
                    continue
                
                # Apply field patterns
                for pattern, key, title, field_type, control in field_patterns:
                    if re.search(pattern, line, re.IGNORECASE) and key not in processed_keys:
                        # Skip witness fields per Modento schema rule (double check)
                        if 'witness' in key.lower() or 'doctor' in key.lower():
                            continue
                        
                        field = FieldInfo(
                            key=key,
                            title=title,
                            field_type=field_type,
                            section=current_section,
                            optional=False,
                            control=control,
                            line_idx=signature_start_idx + i
                        )
                        fields.append(field)
                        processed_keys.add(key)
        
        # ENSURE SIGNATURE FIELD EXISTS (Modento schema requirement)
        if 'signature' not in processed_keys:
            signature_field = FieldInfo(
                key='signature',
                title='Signature',
                field_type='signature',
                section='Signature',
                optional=False,
                control={'hint': None, 'input_type': None},
                line_idx=len(text_lines)
            )
            fields.append(signature_field)
            processed_keys.add('signature')
        
        # ENSURE DATE_SIGNED FIELD EXISTS (Modento schema requirement for consent forms)
        if 'date_signed' not in processed_keys:
            date_signed_field = FieldInfo(
                key='date_signed',
                title='Date Signed',
                field_type='date',
                section='Signature',
                optional=False,
                control={'hint': None, 'input_type': 'any'},
                line_idx=len(text_lines) + 1
            )
            fields.append(date_signed_field)
            processed_keys.add('date_signed')
        
        # REORDER FIELDS: For consent forms, order should be:
        # 1. Form section fields (using the consent title as section name)
        # 2. Primary input fields (relationship, etc.) that come BEFORE printed_name_if_signed_on_behalf
        # 3. signature field
        # 4. date_signed field
        # 5. Secondary fields like printed_name_if_signed_on_behalf
        form_fields = [f for f in fields if f.section == consent_section_name]
        signature_section_fields = [f for f in fields if f.section == 'Signature']
        
        # Separate signature section fields
        signature_field = next((f for f in signature_section_fields if f.field_type == 'signature'), None)
        date_signed_field = next((f for f in signature_section_fields if f.key == 'date_signed'), None)
        
        # Separate primary vs secondary input fields
        # printed_name_if_signed_on_behalf is secondary and should come after signature/date_signed
        primary_input_fields = [f for f in signature_section_fields 
                               if f.field_type in ['input', 'date'] 
                               and f.key not in ['date_signed', 'printed_name_if_signed_on_behalf']]
        secondary_input_fields = [f for f in signature_section_fields 
                                 if f.key == 'printed_name_if_signed_on_behalf']
        other_fields = [f for f in signature_section_fields 
                       if f not in primary_input_fields 
                       and f not in secondary_input_fields
                       and f != signature_field 
                       and f != date_signed_field]
        
        # Build ordered list
        reordered_fields = form_fields + primary_input_fields
        if signature_field:
            reordered_fields.append(signature_field)
        if date_signed_field:
            reordered_fields.append(date_signed_field)
        reordered_fields.extend(secondary_input_fields)
        reordered_fields.extend(other_fields)
        
        fields = reordered_fields
        
        return fields
    
    def _is_witness_or_doctor_signature_field(self, line_lower: str) -> bool:
        """Check if a line represents a field that should be excluded"""
        
        # UNIVERSAL WITNESS FIELD EXCLUSION: Per requirements, we do not allow witnesses on forms or consents
        
        # Witness field indicators - these should be filtered out universally
        witness_indicators = [
            'witness signature', 'witness printed name', 'witness name', 'witness date',
            'witnessed by', 'witness:', 'witness relationship', "witness's", 'witness\u2019s'
        ]
        
        # Doctor/dentist signature indicators - these are typically not patient-facing fields
        doctor_signatures = [
            'doctor signature', 'dentist signature', 'physician signature',
            'dr. signature', 'practitioner signature', 'provider signature', 
            'clinician signature', "doctor's", 'doctor\u2019s'
        ]
        
        # Parent/Guardian signature indicators - these are typically not patient-facing fields
        parent_guardian_signatures = [
            'parent signature', 'guardian signature', 'parent\u2019s signature', 
            "parent's signature", 'guardian\u2019s signature', "guardian's signature",
            'legal guardian\u2019s', "legal guardian's"
        ]
        
        # Filter out witness fields universally
        for indicator in witness_indicators:
            if indicator in line_lower:
                return True
        
        # Filter out clear doctor/provider signatures
        for indicator in doctor_signatures:
            if indicator in line_lower:
                return True
        
        # Filter out parent/guardian signatures
        for indicator in parent_guardian_signatures:
            if indicator in line_lower:
                return True
        
        # Filter lines mentioning "patient/parent/guardian" signature or name fields
        if 'patient/parent/guardian' in line_lower:
            return True
        
        # Special handling: "legally authorized representative" - filter if witness-related
        if 'legally authorized representative' in line_lower:
            return True
        
        # Check for printed name in context of witness/representative - filter these out
        if 'printed name' in line_lower:
            # Filter if it's clearly witness context
            if any(context in line_lower for context in ['witness', 'guardian', 'parent']):
                return True
        
        # Filter lines that are mostly or entirely underscores (signature lines)
        # Strip HTML tags first to check the actual content
        text_only = re.sub(r'<[^>]+>', '', line_lower).strip()
        if text_only and len(text_only) >= 10:  # Only check if there's substantial content
            underscore_count = text_only.count('_')
            if underscore_count >= 10 and underscore_count / len(text_only) > 0.7:
                return True
            
        return False
    
    def _remove_witness_and_doctor_signatures(self, content: str) -> str:
        """Remove witness and doctor signature text from HTML content"""
        
        # Split content into lines for processing
        lines = content.split('<br>')
        filtered_lines = []
        
        for line in lines:
            # Strip HTML tags to check content
            text_content = re.sub(r'<[^>]+>', '', line).strip()
            
            # Skip lines that contain witness or doctor signature patterns
            if text_content and not self._is_witness_or_doctor_signature_field(text_content.lower()):
                filtered_lines.append(line)
        
        # Rejoin the filtered lines
        return '<br>'.join(filtered_lines)
    
    def _create_enhanced_consent_html(self, consent_text_lines: List[str], full_text: str, provider_patterns: List[str], bold_lines: Optional[Dict[str, bool]] = None) -> Tuple[str, Optional[str]]:
        """Create properly formatted HTML content for consent forms with provider placeholders
        
        Args:
            consent_text_lines: Lines of consent text
            full_text: Full text for pattern analysis
            provider_patterns: Patterns for provider placeholder replacement
            bold_lines: Dictionary mapping line text to whether it's bold (from DOCX)
        
        Returns:
            Tuple of (html_content, detected_title)
        """
        
        if bold_lines is None:
            bold_lines = {}
        
        # Extract title from first line if it's a header
        title = None
        content_lines = consent_text_lines.copy()
        
        if content_lines and content_lines[0].startswith('## '):
            title = content_lines[0].replace('## ', '').strip()
            content_lines = content_lines[1:]  # Remove title from content
        elif content_lines and re.match(r'^[A-Z\s]+CONSENT[A-Z\s]*$', content_lines[0]):
            # Match all caps titles like "TOOTH REMOVAL CONSENT FORM"
            title = content_lines[0].strip()
            content_lines = content_lines[1:]
        elif content_lines and re.match(r'^Informed\s+Consent\s+for\s+', content_lines[0], re.IGNORECASE):
            # Match titles like "Informed Consent for Crown And Bridge Prosthetics"
            title = content_lines[0].strip()
            content_lines = content_lines[1:]
        elif content_lines and re.match(r'^\*\*(.+)\*\*$', content_lines[0]):
            # Match bold markdown titles like "**Olympia Hills Family Dental Warranty Document**"
            match = re.match(r'^\*\*(.+)\*\*$', content_lines[0])
            if match and len(match.group(1)) < 150:  # Reasonable title length
                title = match.group(1).strip()
                content_lines = content_lines[1:]  # Remove title from content
        
        # Process content to handle bullet points and structure
        processed_lines = []
        in_bullet_list = False
        prev_line_was_bold_subheader = False
        
        for line in content_lines:
            if not line.strip():
                if in_bullet_list:
                    processed_lines.append('</ul>')
                    in_bullet_list = False
                continue
            
            # Clean markdown formatting from the line before processing
            line = self._clean_markdown_formatting(line)
            
            # Check if this line is a bold subheader from DOCX
            is_bold_subheader = False
            line_text = line.strip()
            if line_text in bold_lines and bold_lines[line_text]:
                # This is a bold line from DOCX - check if it's likely a subheader
                # Subheaders are typically short (< 100 chars), not bullet points, and not field labels
                is_bullet = re.match(r'^[-•\uf0b7]\s+', line_text)
                has_underscores = '_' in line_text
                is_short = len(line_text) < 100
                
                if not is_bullet and not has_underscores and is_short:
                    is_bold_subheader = True
            
            # Add spacing before bold subheaders (except if it's the first line or follows another subheader)
            if is_bold_subheader and processed_lines and not prev_line_was_bold_subheader:
                # Add extra spacing before subheader
                processed_lines.append('<br>')
            
            # Check if line is a bullet point (starts with - or \uf0b7 or bullet marker)
            if re.match(r'^[-•\uf0b7]\s+', line.strip()):
                if not in_bullet_list:
                    processed_lines.append('<ul>')
                    in_bullet_list = True
                # Remove bullet marker and add as list item, also clean \uf0b7 from within the text
                clean_line = re.sub(r'^[-•\uf0b7]\s+', '', line.strip())
                clean_line = clean_line.replace('\uf0b7', '').strip()
                processed_lines.append(f'<li>{clean_line}</li>')
                prev_line_was_bold_subheader = False
            else:
                if in_bullet_list:
                    processed_lines.append('</ul>')
                    in_bullet_list = False
                
                # Apply bold formatting to subheaders
                if is_bold_subheader:
                    processed_lines.append(f'<strong>{line.strip()}</strong>')
                    prev_line_was_bold_subheader = True
                else:
                    processed_lines.append(line.strip())
                    prev_line_was_bold_subheader = False
        
        # Close bullet list if still open
        if in_bullet_list:
            processed_lines.append('</ul>')
        
        # Join content - avoid extra <br> tags around <ul> tags
        content_parts = []
        for i, line in enumerate(processed_lines):
            if i > 0 and not (line.startswith('<ul>') or line.startswith('</ul>') or 
                             processed_lines[i-1].startswith('<ul>') or processed_lines[i-1].startswith('</ul>') or
                             line.startswith('<li>') or line.endswith('</li>')):
                content_parts.append('<br>')
            content_parts.append(line)
        content = ''.join(content_parts)
        
        # Remove practice header/footer information
        content = self._remove_practice_header_footer(content)
        
        # Apply provider placeholder substitution
        for pattern in provider_patterns:
            content = re.sub(pattern, '{{provider}}', content, flags=re.IGNORECASE)
        
        # Also replace common Dr. blank patterns
        content = re.sub(r'Dr\.\s+_+', 'Dr. {{provider}}', content, flags=re.IGNORECASE)
        
        # Replace tooth number/site placeholders - match various patterns with or without underscores
        # Pattern: "Tooth Number: ___" with underscores first (most specific)
        content = re.sub(r'Tooth\s+Number\s*:\s*_+', 'Tooth Number: {{tooth_or_site}}', content, flags=re.IGNORECASE)
        # Pattern: "Tooth Number:" without underscores (avoid replacing already replaced text)
        content = re.sub(r'Tooth\s+Number\s*:(?!\s*\{\{)', 'Tooth Number: {{tooth_or_site}}', content, flags=re.IGNORECASE)
        
        # Pattern: "Tooth No(s). ___" with underscores
        content = re.sub(r'Tooth\s+No\(s\)\.\s+_+', 'Tooth No(s). {{tooth_or_site}}', content, flags=re.IGNORECASE)
        # Pattern: "Tooth No. ___" with underscores
        content = re.sub(r'Tooth\s+No\.\s*:\s*_+', 'Tooth No.: {{tooth_or_site}}', content, flags=re.IGNORECASE)
        # Pattern: "Tooth #: ___" with underscores
        content = re.sub(r'Tooth\s*#\s*:\s*_+', 'Tooth #: {{tooth_or_site}}', content, flags=re.IGNORECASE)
        
        # Replace patient name placeholders - match various patterns with or without underscores
        # Pattern: "Patient name: ___" with underscores first (most specific)
        content = re.sub(r'Patient\s+[Nn]ame\s*:\s*_+', 'Patient Name: {{patient_name}}', content, flags=re.IGNORECASE)
        # Pattern: "Patient Name:" without underscores (avoid replacing already replaced text)
        content = re.sub(r'Patient\s+[Nn]ame\s*:(?!\s*\{\{)', 'Patient Name: {{patient_name}}', content, flags=re.IGNORECASE)
        
        # Pattern: "I, _____(print name)" or similar variations
        content = re.sub(r'\b[Ii],?\s+_+\s*\(?\s*print\s+name\s*\)?', 'I, {{patient_name}} (print name)', content, flags=re.IGNORECASE)
        
        # Replace DOB placeholders - match various patterns with or without underscores
        # Pattern: "DOB: ___" with underscores first (most specific)
        content = re.sub(r'DOB\s*:\s*_+', 'DOB: {{patient_dob}}', content, flags=re.IGNORECASE)
        # Pattern: "DOB:" without underscores (avoid replacing already replaced text)
        content = re.sub(r'DOB\s*:(?!\s*\{\{)', 'DOB: {{patient_dob}}', content, flags=re.IGNORECASE)
        
        # Replace Date of Birth placeholders - match various patterns with or without underscores
        # Pattern: "Date of Birth: ___" with underscores first (most specific)
        content = re.sub(r'Date\s+of\s+Birth\s*:\s*_+', 'Date of Birth: {{patient_dob}}', content, flags=re.IGNORECASE)
        # Pattern: "Date of Birth:" without underscores (avoid replacing already replaced text)
        content = re.sub(r'Date\s+of\s+Birth\s*:(?!\s*\{\{)', 'Date of Birth: {{patient_dob}}', content, flags=re.IGNORECASE)
        
        # Replace Planned Procedure placeholders - match various patterns with or without underscores
        # Pattern: "Planned Procedure: ___" with underscores first (most specific)
        content = re.sub(r'Planned\s+Procedure\s*:\s*_+', 'Planned Procedure: {{planned_procedure}}', content, flags=re.IGNORECASE)
        # Pattern: "Planned Procedure:" without underscores (avoid replacing already replaced text)
        content = re.sub(r'Planned\s+Procedure\s*:(?!\s*\{\{)', 'Planned Procedure: {{planned_procedure}}', content, flags=re.IGNORECASE)
        
        # Replace Diagnosis placeholders - match various patterns with or without underscores
        # Pattern: "Diagnosis: ___" with underscores first (most specific)
        content = re.sub(r'Diagnosis\s*:\s*_+', 'Diagnosis: {{diagnosis}}', content, flags=re.IGNORECASE)
        # Pattern: "Diagnosis:" without underscores (avoid replacing already replaced text)
        content = re.sub(r'Diagnosis\s*:(?!\s*\{\{)', 'Diagnosis: {{diagnosis}}', content, flags=re.IGNORECASE)
        
        # Replace Alternative Treatment placeholders - match various patterns with or without underscores
        # Pattern: "Alternative Treatment: ___" with underscores first (most specific)
        content = re.sub(r'Alternative\s+Treatment\s*:\s*_+', 'Alternative Treatment: {{alternative_treatment}}', content, flags=re.IGNORECASE)
        # Pattern: "Alternative Treatment:" without underscores (avoid replacing already replaced text)
        content = re.sub(r'Alternative\s+Treatment\s*:(?!\s*\{\{)', 'Alternative Treatment: {{alternative_treatment}}', content, flags=re.IGNORECASE)
        
        # Replace standalone Date placeholders (not Date of Birth or Date Signed)
        # Pattern: "Date: ___" with underscores first (most specific)
        content = re.sub(r'(?<!of\s)(?<!Birth\s)(?<!Signed\s)Date\s*:\s*_+', 'Date: {{today_date}}', content, flags=re.IGNORECASE)
        # Pattern: "Date:" without underscores (avoid replacing already replaced text and Date of Birth/Date Signed)
        content = re.sub(r'(?<!of\s)(?<!Birth\s)(?<!Signed\s)Date\s*:(?!\s*\{\{)', 'Date: {{today_date}}', content, flags=re.IGNORECASE)
        
        # Strip witness and doctor signatures from content
        content = self._remove_witness_and_doctor_signatures(content)
        
        # Format as HTML with proper structure
        if title:
            html_content = f'<div style="text-align:center"><strong>{title}</strong><br>'
        else:
            html_content = '<div style="text-align:center"><strong>Informed Consent</strong><br>'
        
        html_content += content
        html_content += '</div>'
        
        return html_content, title
    
    def _clean_markdown_formatting(self, text: str) -> str:
        """Clean markdown formatting artifacts from text and convert to HTML"""
        
        # Remove standalone ## or ### markers (empty headers)
        text = re.sub(r'^###+\s*$', '', text.strip())
        
        # Convert ### headers to strong tags
        text = re.sub(r'^###\s+(.+)$', r'<strong>\1</strong>', text)
        
        # Convert ## headers to strong tags
        text = re.sub(r'^##\s+(.+)$', r'<strong>\1</strong>', text)
        
        # Convert **bold** to <strong>bold</strong>
        text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
        
        # Clean any remaining standalone ## markers within text
        text = re.sub(r'\s*##\s*', ' ', text)
        
        return text.strip()
    
    def _remove_practice_header_footer(self, content: str) -> str:
        """Remove practice header/footer information"""
        
        practice_patterns = [
            r'www\.\w+\.com',
            r'\w+@\w+\.com',
            r'\(\d{3}\)\d{3}-?\d{4}',
            r'\d+\s+[A-Z][A-Za-z\s]+,\s+[A-Z]{2}\s+\d{5}',
            r'Route\s+\d+.*\d{5}',
            r'Smile@.*\.com',
        ]
        
        for pattern in practice_patterns:
            content = re.sub(pattern, '', content, flags=re.IGNORECASE)
        
        # Clean up extra whitespace
        content = re.sub(r'\s+', ' ', content).strip()
        
        return content
    
    def _detect_consent_title(self, content: str) -> Optional[str]:
        """Detect consent form title from content"""
        
        title_patterns = [
            r'Informed\s+Consent\s+for\s+([^.]+)',
            r'Consent\s+for\s+([^.]+)',
            r'([^.]*Consent[^.]*)',
        ]
        
        for pattern in title_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                title = match.group(1).strip()
                # Clean up the title
                title = re.sub(r'\s+', ' ', title)
                return title
        
        return None
    
    def _split_into_paragraphs(self, content: str) -> List[str]:
        """Split content into logical paragraphs for better HTML formatting"""
        
        # Split on sentence boundaries and common section markers
        sections = re.split(r'(?:\.\s+|\n\s*\n)', content)
        
        paragraphs = []
        current_para = ""
        
        for section in sections:
            section = section.strip()
            if not section:
                continue
            
            # If section is very short, combine with current paragraph
            if len(section) < 50 and current_para:
                current_para += " " + section
            else:
                if current_para:
                    paragraphs.append(current_para)
                current_para = section
        
        # Add final paragraph
        if current_para:
            paragraphs.append(current_para)
        
        return paragraphs


class ConsentToJSONConverter:
    """Convert consent documents to JSON format"""
    
    def __init__(self):
        """Initialize the converter"""
        self.extractor = ConsentFormFieldExtractor()
        self.validator = ModentoSchemaValidator()
    
    def convert_consent_to_json(self, file_path: Path, output_path: Optional[Path] = None) -> Dict[str, Any]:
        """Convert a consent document to Modento JSON format"""
        
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Extract text from document
        text_lines, pipeline_info = self.extractor.extract_text_from_document(file_path)
        
        # Extract fields
        fields = self.extractor.extract_consent_form_fields(text_lines, pipeline_info)
        
        # Convert to dict
        spec = []
        for field in fields:
            field_dict = {
                "key": field.key,
                "title": field.title,
                "section": field.section,
                "optional": field.optional,
                "type": field.field_type,
                "control": field.control
            }
            spec.append(field_dict)
        
        # Validate and normalize
        is_valid, errors, spec = self.validator.validate_and_normalize(spec)
        
        # Write output if path provided
        if output_path:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w') as f:
                json.dump(spec, f, indent=2)
        
        # Return result info
        sections = set(field['section'] for field in spec)
        
        return {
            'spec': spec,
            'field_count': len(spec),
            'section_count': len(sections),
            'is_valid': is_valid,
            'errors': errors,
            'pipeline_info': pipeline_info
        }


def process_directory(input_dir: Path, output_dir: Path, verbose: bool = False):
    """Process all consent documents in a directory"""
    
    # Find all PDF and DOCX files
    pdf_files = list(input_dir.glob("*.pdf"))
    docx_files = list(input_dir.glob("*.docx")) + list(input_dir.glob("*.doc"))
    all_files = pdf_files + docx_files
    
    if not all_files:
        print(f"No PDF or DOCX files found in {input_dir}")
        return
    
    print(f"Found {len(all_files)} consent forms to process: {len(pdf_files)} PDF, {len(docx_files)} DOCX")
    
    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Process each file
    converter = ConsentToJSONConverter()
    results = []
    
    for file_path in all_files:
        print(f"\n[+] Processing {file_path.name} ({file_path.suffix.upper().lstrip('.')}) ...")
        
        try:
            output_path = output_dir / f"{file_path.stem}.json"
            result = converter.convert_consent_to_json(file_path, output_path)
            
            print(f"[✓] Wrote JSON: {output_path}")
            print(f"[i] Sections: {result['section_count']} | Fields: {result['field_count']}")
            
            if verbose:
                pipeline = result['pipeline_info']
                print(f"[i] Pipeline/Backend: {pipeline['pipeline']}/{pipeline['backend']}")
                if pipeline.get('ocr_used'):
                    print(f"[i] OCR ({pipeline['ocr_engine']}): used")
                else:
                    print(f"[i] OCR: not required (native text extraction)")
            
            results.append({
                "file": file_path.name,
                "format": file_path.suffix.upper().lstrip('.'),
                "success": True,
                "fields": result['field_count'],
                "sections": result['section_count']
            })
            
        except Exception as e:
            print(f"[x] Error processing {file_path.name}: {e}")
            results.append({
                "file": file_path.name,
                "format": file_path.suffix.upper().lstrip('.'),
                "success": False,
                "error": str(e)
            })
    
    successful = sum(1 for r in results if r.get("success", False))
    print(f"\n[i] Successfully processed: {successful}/{len(results)} consent forms")


def main():
    """Command line interface for consent form conversion"""
    parser = argparse.ArgumentParser(
        description="Convert consent form PDFs and DOCX to Modento JSON format",
        epilog="This converter is specifically designed for consent forms with all required rules and formatting."
    )
    parser.add_argument("path", nargs='?', default=None, help="Path to consent PDF/DOCX file or directory")
    parser.add_argument("--output", "-o", help="Output JSON file path (for single file)")
    parser.add_argument("--output-dir", help="Output directory path (for batch processing)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    # Validate input path
    if args.path is None:
        parser.print_help()
        sys.exit(1)
    
    input_path = Path(args.path)
    if not input_path.exists():
        print(f"Error: Path not found: {input_path}")
        sys.exit(1)
    
    # Check if input is a directory (batch mode) or file (single mode)
    if input_path.is_dir():
        # Batch processing mode
        if args.output_dir:
            output_dir = Path(args.output_dir)
        else:
            output_dir = input_path / "consent_json_output"
        
        try:
            process_directory(input_path, output_dir, args.verbose)
        except Exception as e:
            print(f"Error: {e}")
            sys.exit(1)
    
    elif input_path.is_file():
        # Single file processing mode
        supported_extensions = {'.pdf', '.docx', '.doc'}
        if input_path.suffix.lower() not in supported_extensions:
            print(f"Error: Unsupported file format '{input_path.suffix}'. Supported formats: PDF, DOCX")
            sys.exit(1)
        
        if args.output:
            output_path = Path(args.output)
        else:
            output_path = input_path.with_suffix('.json')
        
        try:
            converter = ConsentToJSONConverter()
            result = converter.convert_consent_to_json(input_path, output_path)
            
            print(f"\n[✓] Conversion complete!")
            print(f"[i] Output: {output_path}")
            print(f"[i] Fields detected: {result['field_count']}")
            print(f"[i] Sections detected: {result['section_count']}")
            print(f"[i] Schema validation: {'PASSED' if result['is_valid'] else 'FAILED'}")
            
            if args.verbose:
                if result['errors']:
                    print("\n[!] Validation issues:")
                    for error in result['errors']:
                        print(f"    - {error}")
                
                print(f"\n[i] Pipeline details:")
                for key, value in result['pipeline_info'].items():
                    print(f"    - {key}: {value}")
            
        except Exception as e:
            print(f"Error: {e}")
            sys.exit(1)
    
    else:
        print(f"Error: Path is neither a file nor directory: {input_path}")
        sys.exit(1)


if __name__ == "__main__":
    main()
