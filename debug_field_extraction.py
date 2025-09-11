#!/usr/bin/env python3
"""Debug field extraction to understand why work address fields are missing"""

import sys
from pdf_to_json_converter import PDFFormFieldExtractor
from docling.document_converter import DocumentConverter

def debug_field_extraction(pdf_path):
    # Extract text from PDF
    converter = DocumentConverter()
    result = converter.convert(pdf_path)
    text_lines = result.document.export_to_text().split('\n')
    
    # Initialize extractor
    extractor = PDFFormFieldExtractor()
    
    # Find all address-related lines and check field extraction
    print("=== Debugging all address field extractions ===")
    seen_fields_global = set()
    
    for i, line in enumerate(text_lines):
        # Pass context to the method
        context_lines = text_lines[max(0, i-3):i+3]
        inline_fields = extractor.parse_inline_fields(line, context_lines)
        if inline_fields:
            has_address_field = any(field[0].lower() in ['street', 'city', 'state', 'zip'] 
                                   for field in inline_fields)
            if has_address_field:
                print(f"\nLine {i}: {line}")
                print(f"Extracted fields: {inline_fields}")
                
                # Check context
                context_lines_text = ' '.join(text_lines[max(0, i-3):i+3]).lower()
                if 'work address' in context_lines_text:
                    print("  ✓ Work address context detected")
                elif 'if different' in context_lines_text:
                    print("  ✓ 'If different' context detected")
                else:
                    print("  - No special context")
                
                # Track seen fields
                for field_name, _ in inline_fields:
                    if field_name.lower() in ['street', 'city', 'state', 'zip']:
                        if field_name in seen_fields_global:
                            print(f"    WARNING: {field_name} already seen before")
                        else:
                            seen_fields_global.add(field_name)

if __name__ == "__main__":
    debug_field_extraction('pdfs/npf.pdf')