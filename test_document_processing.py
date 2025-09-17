#!/usr/bin/env python3
"""
Test the new document processing module
"""

import sys
from pathlib import Path

# Add the parent directory to sys.path so we can import our modules
sys.path.append('.')

from document_processing.text_extractor import DocumentTextExtractor
from document_processing.form_classifier import FormClassifier

def test_document_processing():
    """Test the document processing modules"""
    print("Testing Document Processing Modules")
    print("=" * 50)
    
    # Test text extraction
    extractor = DocumentTextExtractor()
    classifier = FormClassifier()
    
    # Test with NPF PDF
    pdf_path = Path("pdfs/npf.pdf")
    if pdf_path.exists():
        print(f"[+] Testing text extraction from {pdf_path}")
        text_lines, pipeline_info = extractor.extract_text_from_document(pdf_path)
        print(f"[i] Extracted {len(text_lines)} lines")
        print(f"[i] Pipeline info: {pipeline_info}")
        
        # Test form classification
        form_type = classifier.detect_form_type(text_lines)
        print(f"[i] Detected form type: {form_type}")
        
        # Show first few lines
        print(f"[i] First 5 lines:")
        for i, line in enumerate(text_lines[:5]):
            print(f"  {i+1}: {line}")
        
        return True
    else:
        print(f"[!] PDF file not found: {pdf_path}")
        return False

if __name__ == "__main__":
    success = test_document_processing()
    if success:
        print("\n[✓] Document processing module test passed!")
    else:
        print("\n[✗] Document processing module test failed!")
        sys.exit(1)