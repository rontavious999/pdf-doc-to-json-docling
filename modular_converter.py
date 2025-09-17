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
    """Modular version of DocumentToJSONConverter"""
    
    def __init__(self):
        self.extractor = ModularDocumentFormFieldExtractor()
        self.validator = ModentoSchemaValidator()
        self.enhanced_consent_processor = None
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
        """Convert a PDF or DOCX to Modento Forms JSON with modular processing"""
        # Use the original converter logic but with modular text extraction
        # Import and delegate to the backup converter for full logic
        from pdf_to_json_converter_backup import DocumentToJSONConverter
        legacy_converter = DocumentToJSONConverter()
        
        # Replace the extractor with our modular one for text extraction and form classification
        original_extractor = legacy_converter.extractor
        legacy_converter.extractor = self.extractor
        
        try:
            # Use the original conversion logic
            result = legacy_converter.convert_document_to_json(document_path, output_path)
            return result
        finally:
            # Restore original extractor
            legacy_converter.extractor = original_extractor


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