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
            
            # Remove null hints
            if 'hint' in ctrl and ctrl['hint'] is None:
                del ctrl['hint']
            
            if q_type == "input":
                t = ctrl.get("input_type")
                if t not in cls.VALID_INPUT_TYPES:
                    ctrl["input_type"] = "name"
            
            if q_type == "date":
                t = ctrl.get("input_type")
                if t not in {"past","future"}:
                    if "input_type" in ctrl:
                        del ctrl["input_type"]
            
            if q_type == "signature":
                ctrl.clear()
        
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
        
        # Consent-specific field patterns for better extraction
        self.consent_field_patterns = {
            'printed_name': re.compile(r'(?:printed?\\s*name|print\\s*name|name\\s*\\(print\\)|patient\\s*print)', re.IGNORECASE),
            'date_of_birth': re.compile(r'(?:date\\s*of\\s*birth|birth\\s*date|dob|born)', re.IGNORECASE),
            'relationship': re.compile(r'(?:relationship|relation\\s*to|guardian|parent|spouse)', re.IGNORECASE),
            'consent_date': re.compile(r'(?:consent\\s*date|date\\s*of\\s*consent|today)', re.IGNORECASE),
        }
    
    def extract_text_from_document(self, file_path: Path) -> Tuple[List[str], Dict[str, Any]]:
        """Extract text from PDF or DOCX document using Docling"""
        
        result = self.converter.convert(str(file_path))
        doc = result.document
        
        # Extract text content
        text_content = doc.export_to_text()
        text_lines = [line.strip() for line in text_content.split('\n') if line.strip()]
        
        # Get pipeline information
        pipeline_info = {
            'pipeline': result.input.format.name if result.input else 'Unknown',
            'backend': 'DoclingParseDocumentBackend',
            'document_format': file_path.suffix.upper().lstrip('.'),
            'ocr_used': file_path.suffix.lower() == '.pdf',
            'ocr_engine': 'EasyOCR' if file_path.suffix.lower() == '.pdf' else None
        }
        
        return text_lines, pipeline_info
    
    def extract_consent_form_fields(self, text_lines: List[str]) -> List[FieldInfo]:
        """Extract fields specifically for consent forms"""
        
        fields = []
        processed_keys = set()
        current_section = "Form"
        
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
        field_patterns = [
            (r'Patient.*Name.*Print', 'patient_name_print', 'Patient Name (Print)', 'input', {'input_type': 'name'}),
            (r'Patient.*Name(?!\s*\()', 'patient_name', 'Patient Name', 'input', {'input_type': 'name'}),
            (r'Printed?\s+Name', 'printed_name', 'Printed Name', 'input', {'input_type': 'name'}),
            (r'Date\s*:?\s*$', 'date_signed', 'Date Signed', 'date', {'input_type': 'past'}),
            (r'Date\s+of\s+Birth', 'date_of_birth', 'Date of Birth', 'date', {'input_type': 'past'}),
            (r'Relationship.*(?:minor|patient)', 'relationship', 'Relationship', 'input', {'input_type': 'name'}),
            (r'Authorized\s+Representative', 'authorized_representative', 'Authorized Representative', 'input', {'input_type': 'name'}),
            (r'legal\s+guardian', 'legal_guardian', 'Legal Guardian', 'input', {'input_type': 'name'}),
            (r'tooth\s+no(?:mber)?\.?\s*:?\s*__+', 'tooth_number', 'Tooth Number', 'input', {'input_type': 'name'}),
            (r'procedure.*follows?', 'procedure_description', 'Procedure Description', 'input', {'input_type': 'name'}),
            (r'alternative.*treatment', 'alternative_treatment', 'Alternative Treatment', 'input', {'input_type': 'name'}),
        ]
        
        # EXTRACT MAIN CONSENT TEXT BLOCK
        consent_text_lines = []
        signature_start_idx = None
        
        for i, line in enumerate(text_lines):
            line_lower = line.lower()
            if any(sig_pattern in line_lower for sig_pattern in ['signature:', 'patient name', 'printed name:', 'date:']):
                signature_start_idx = i
                break
            elif line.strip() and not line.startswith('#'):
                consent_text_lines.append(line.strip())
        
        if consent_text_lines:
            # Create main consent text field with provider placeholders
            consent_html = self._create_enhanced_consent_html(consent_text_lines, full_text, provider_patterns)
            
            consent_field = FieldInfo(
                key='form_1',
                title='',
                field_type='text',
                section='Form',
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
                
                # Apply field patterns
                for pattern, key, title, field_type, control in field_patterns:
                    if re.search(pattern, line, re.IGNORECASE) and key not in processed_keys:
                        # Skip witness fields per Modento schema rule
                        if 'witness' in key.lower():
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
                control={},
                line_idx=len(text_lines)
            )
            fields.append(signature_field)
            processed_keys.add('signature')
        
        return fields
    
    def _create_enhanced_consent_html(self, consent_text_lines: List[str], full_text: str, provider_patterns: List[str]) -> str:
        """Create properly formatted HTML content for consent forms with provider placeholders"""
        
        # Clean and join text
        content = ' '.join(consent_text_lines)
        content = re.sub(r'\s+', ' ', content).strip()
        
        # Remove practice header/footer information
        content = self._remove_practice_header_footer(content)
        
        # Apply provider placeholder substitution
        for pattern in provider_patterns:
            content = re.sub(pattern, 'Dr. {{provider}}', content, flags=re.IGNORECASE)
        
        # Format consent text
        content = self.consent_shaper.format_consent_text(content)
        
        # Detect form title/type
        title = self._detect_consent_title(content)
        
        # Format as HTML with proper structure
        if title:
            html_content = f'<div style="text-align:center"><strong>{title}</strong><br>'
        else:
            html_content = '<div style="text-align:center"><strong>Informed Consent</strong><br>'
        
        # Add main content - split into logical paragraphs
        paragraphs = self._split_into_paragraphs(content)
        html_content += '<br>'.join(paragraphs)
        html_content += '</div>'
        
        return html_content
    
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
        fields = self.extractor.extract_consent_form_fields(text_lines)
        
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
