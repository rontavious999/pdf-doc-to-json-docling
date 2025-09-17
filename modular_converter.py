"""
Modular PDF to JSON Converter

This is a modular version that integrates the new modules while maintaining compatibility.
"""

import sys
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

# Import the new modules
from document_processing.text_extractor import DocumentTextExtractor
from document_processing.form_classifier import FormClassifier
from field_detection.field_detector import FieldDetector
from field_detection.input_detector import InputDetector
from field_detection.radio_detector import RadioDetector
from content_processing.section_manager import SectionManager
from field_validation.field_normalizer import FieldNormalizer

# Import existing components
from pdf_to_json_converter_backup import ModentoSchemaValidator, FieldInfo, DocumentToJSONConverter


class ModularDocumentFormFieldExtractor:
    """Modular version of DocumentFormFieldExtractor using new modules"""
    
    def __init__(self):
        # Initialize all modules
        self.text_extractor = DocumentTextExtractor()
        self.form_classifier = FormClassifier()
        self.field_detector = FieldDetector()
        self.input_detector = InputDetector()
        self.radio_detector = RadioDetector()
        self.section_manager = SectionManager()
        self.field_normalizer = FieldNormalizer()
        
        # For compatibility with existing methods, we'll delegate to the backup converter
        # Import the backup converter's extractor
        from pdf_to_json_converter_backup import DocumentFormFieldExtractor
        self._legacy_extractor = DocumentFormFieldExtractor()
    
    def extract_text_from_document(self, document_path: Path) -> Tuple[List[str], Dict[str, Any]]:
        """Extract text using the new modular text extractor"""
        return self.text_extractor.extract_text_from_document(document_path)
    
    def detect_form_type(self, text_lines: List[str]) -> str:
        """Detect form type using the new modular classifier"""
        return self.form_classifier.detect_form_type(text_lines)
    
    def extract_fields_from_text(self, text_lines: List[str]) -> List[FieldInfo]:
        """Extract fields using modular approach but delegate complex logic to legacy for now"""
        # For now, use the legacy extractor to maintain exact compatibility
        # In a full implementation, we would rewrite this using the modules
        return self._legacy_extractor.extract_fields_from_text(text_lines)
    
    # Delegate all other methods to legacy extractor for compatibility
    def __getattr__(self, name):
        return getattr(self._legacy_extractor, name)


class ModularDocumentToJSONConverter:
    """Modular version of DocumentToJSONConverter using new field processing managers"""
    
    def __init__(self):
        self.extractor = ModularDocumentFormFieldExtractor()
        self.validator = ModentoSchemaValidator()
        self.enhanced_consent_processor = None
        
        # Initialize field processing managers 
        from field_processing import (
            FieldOrderingManager, 
            FieldNormalizationManager, 
            ConsentShapingManager,
            HeaderFooterManager
        )
        self.field_ordering_manager = FieldOrderingManager()
        self.field_normalization_manager = FieldNormalizationManager()
        self.consent_shaping_manager = ConsentShapingManager()
        self.header_footer_manager = HeaderFooterManager()
        
        self._setup_enhanced_processors()
    
    def _setup_enhanced_processors(self):
        """Setup enhanced processors for specific form types"""
        try:
            # Import enhanced consent processor if available
            from enhanced_docx_processor import EnhancedConsentProcessor
            self.enhanced_consent_processor = EnhancedConsentProcessor()
            print("[i] Enhanced consent processing available")
        except ImportError:
            print("[i] Enhanced consent processing unavailable - using standard processing")
    
    def convert_document_to_json(self, document_path: Path, output_path: Optional[Path] = None) -> Dict[str, Any]:
        """Convert a PDF or DOCX to Modento Forms JSON with truly modular processing"""
        # Start processing message
        document_type = "DOCX" if document_path.suffix.lower() in ['.docx', '.doc'] else "PDF"
        print(f"[+] Processing {document_path.name} ({document_type}) ...")
        
        # For DOCX files, try enhanced consent processing first
        if (document_type == "DOCX" and 
            self.enhanced_consent_processor and 
            "consent" in document_path.name.lower()):
            
            try:
                # Extract text to detect form type
                text_lines, _ = self.extractor.extract_text_from_document(document_path)
                form_type = self.enhanced_consent_processor.detect_consent_form_type(text_lines)
                
                if form_type:
                    print(f"[i] Using enhanced consent processing for {form_type}")
                    result = self.enhanced_consent_processor.process_docx_file(document_path)
                    
                    # Save to file if output path provided
                    if output_path:
                        self._save_result_to_file(result["spec"], output_path, result)
                    
                    return result
            except Exception as e:
                print(f"[!] Enhanced consent processing failed: {e}, falling back to standard processing")
        
        # Standard modular processing 
        # Extract text from document using modular text extractor
        text_lines, pipeline_info = self.extractor.extract_text_from_document(document_path)
        if not text_lines:
            raise ValueError(f"Could not extract text from document: {document_path}")
        
        # Extract form fields (this still delegates to legacy for complex logic)
        # TODO: This could be further modularized by breaking down extract_fields_from_text
        fields = self.extractor.extract_fields_from_text(text_lines)
        
        # Apply field processing using new managers (THIS IS THE KEY IMPROVEMENT)
        fields = self._process_fields_with_managers(fields)
        
        # Convert to Modento format
        json_spec = self._convert_fields_to_json_spec(fields)
        
        # Apply final normalizations using managers
        json_spec = self._apply_final_normalizations(json_spec)
        
        # Validate and normalize
        is_valid, errors, normalized_spec = self.validator.validate_and_normalize(json_spec)
        
        # Final signature validation and cleanup
        normalized_spec = self._ensure_signature_compliance(normalized_spec)
        
        # Final cleanup and text normalization
        normalized_spec = self._apply_final_cleanup(normalized_spec)
        
        # Count sections and remove meta fields
        section_count = len(set(field.get("section", "Unknown") for field in normalized_spec))
        for field in normalized_spec:
            field.pop("meta", None)
        
        # Save to file if output path provided
        if output_path:
            self._save_result_to_file(normalized_spec, output_path, {
                "field_count": len(normalized_spec),
                "section_count": section_count,
                "pipeline_info": pipeline_info
            })
        
        return {
            "spec": normalized_spec,
            "is_valid": is_valid,
            "errors": errors,
            "field_count": len(normalized_spec),
            "section_count": section_count,
            "pipeline_info": pipeline_info
        }
    
    def _process_fields_with_managers(self, fields):
        """Process fields using the new field processing managers"""
        from field_processing import FieldInfo
        
        # Ensure required signature fields are present
        fields = self.field_ordering_manager.ensure_required_signature_fields(fields)
        fields = self.field_ordering_manager.ensure_date_signed_field(fields)
        
        # Order fields properly
        fields = self.field_ordering_manager.order_fields(fields)
        
        return fields
    
    def _convert_fields_to_json_spec(self, fields):
        """Convert FieldInfo objects to JSON specification format"""
        json_spec = []
        
        for field in fields:
            # Normalize control structure using the normalization manager
            normalized_control = self.field_normalization_manager._normalize_control_by_type(
                field.control, field.field_type, field.key
            )
            
            field_dict = {
                "key": field.key,
                "type": field.field_type,
                "title": field.title,
                "control": normalized_control,
                "section": field.section,
                "optional": field.optional
            }
            
            # Transfer line_idx for ordering
            field_dict["meta"] = {"line_idx": getattr(field, 'line_idx', len(json_spec))}
            
            json_spec.append(field_dict)
        
        return json_spec
    
    def _apply_final_normalizations(self, json_spec):
        """Apply final normalizations using the managers"""
        # Apply key normalizations
        json_spec = self.field_normalization_manager.normalize_field_keys(json_spec)
        
        # Apply consent shaping if this is a consent form
        json_spec = self.consent_shaping_manager.apply_consent_shaping(json_spec)
        
        # Normalize text content
        json_spec = self.field_normalization_manager.normalize_text_content(json_spec)
        
        # Normalize authorization field
        json_spec = self.field_normalization_manager.normalize_authorization_field(json_spec)
        
        return json_spec
    
    def _ensure_signature_compliance(self, normalized_spec):
        """Ensure signature compliance with Modento schema"""
        signature_fields = [field for field in normalized_spec if field.get('type') == 'signature']
        
        if len(signature_fields) > 1:
            # Keep only the first one and set canonical key
            first_sig = signature_fields[0]
            first_sig['key'] = 'signature'
            # Remove others
            normalized_spec = [field for field in normalized_spec if not (field.get('type') == 'signature' and field != first_sig)]
        elif len(signature_fields) == 1:
            # Ensure canonical key
            signature_fields[0]['key'] = 'signature'
        elif len(signature_fields) == 0:
            # Add missing signature field
            normalized_spec.append({
                "key": "signature",
                "title": "Signature", 
                "section": "Signature",
                "optional": False,
                "type": "signature",
                "control": {}
            })
        
        return normalized_spec
    
    def _apply_final_cleanup(self, normalized_spec):
        """Apply final cleanup to normalized specification"""
        for field in normalized_spec:
            control = field.get('control', {})
            
            # Fix state fields - they should have empty control in reference
            if field.get('type') == 'states':
                field['control'] = {}
            
            # Fix signature fields - they should have empty control in reference  
            if field.get('type') == 'signature':
                field['control'] = {}
            
            # Clean up field titles using normalization manager
            if 'title' in field:
                field['title'] = self.field_normalization_manager._normalize_title(field['title'])
        
        return normalized_spec
    
    def _save_result_to_file(self, spec, output_path, result_info):
        """Save the JSON specification to a file with proper messaging"""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(spec, f, indent=2, ensure_ascii=False)
        
        # Success message with requested format
        print(f"[✓] Wrote JSON: {output_path.parent.name}/{output_path.name}")
        print(f"[i] Sections: {result_info.get('section_count', 0)} | Fields: {result_info.get('field_count', len(spec))}")
        
        pipeline_info = result_info.get('pipeline_info', {})
        print(f"[i] Pipeline/Model/Backend used: {pipeline_info.get('pipeline', 'Unknown')}/{pipeline_info.get('backend', 'Unknown')}")
        
        # Show appropriate processing info based on document type
        if pipeline_info.get('document_format') == 'DOCX':
            print(f"[i] Document format: DOCX (native text extraction)")
        else:
            ocr_status = "used" if pipeline_info.get('ocr_enabled', False) else "not used"
            print(f"[x] OCR ({pipeline_info.get('ocr_engine', 'Unknown')}): {ocr_status}")


def main():
    """Main entry point using modular converter"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Convert PDF and DOCX forms to Modento JSON format using Docling (Modular Version)')
    parser.add_argument('path', nargs='?', default='pdfs', 
                       help='Path to PDF/DOCX file or directory (defaults to \'pdfs\' directory)')
    parser.add_argument('--output', '-o', 
                       help='Output JSON file path (for single file) or output directory (for batch)')
    parser.add_argument('--verbose', '-v', action='store_true', 
                       help='Verbose output')
    
    args = parser.parse_args()
    
    # Use modular converter
    converter = ModularDocumentToJSONConverter()
    
    input_path = Path(args.path)
    
    try:
        if input_path.is_file():
            # Single file processing
            output_path = None
            if args.output:
                output_path = Path(args.output)
            else:
                output_path = input_path.with_suffix('.json')
            
            result = converter.convert_document_to_json(input_path, output_path)
            print(f"[✓] Conversion completed: {output_path}")
            
        elif input_path.is_dir():
            # Directory processing
            from pdf_to_json_converter_backup import process_directory
            output_dir = Path(args.output) if args.output else input_path / 'json_output'
            process_directory(input_path, output_dir, args.verbose)
            
        else:
            print(f"[!] Path not found: {input_path}")
            sys.exit(1)
            
    except Exception as e:
        print(f"[!] Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()