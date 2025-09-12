#!/usr/bin/env python3
"""
Debug field processing order and line indices
"""
import json
from pathlib import Path
from pdf_to_json_converter import PDFFormFieldExtractor

def debug_field_order():
    """Debug the field processing order in patient info form extraction"""
    
    extractor = PDFFormFieldExtractor()
    pdf_path = Path("pdfs/npf.pdf")
    
    # Extract raw text
    text_lines, pipeline_info = extractor.extract_text_from_pdf(pdf_path)
    
    # Extract fields using patient info form method
    fields = extractor.extract_patient_info_form_fields(text_lines)
    
    print("=== EXTRACTED FIELDS WITH LINE ORDER ===")
    print(f"Total fields extracted: {len(fields)}")
    print()
    
    # Show first 15 fields with their line indices and processing order
    for i, field in enumerate(fields[:15]):
        line_idx = field.line_idx if hasattr(field, 'line_idx') else 'unknown'
        print(f"{i+1:2d}. {field.key:35} (line {line_idx:3}) {field.title}")
    
    # Check what's on the key lines
    print("\n=== KEY LINES FROM TEXT ===")
    key_lines = [3, 5, 7, 8, 10, 11]  # Lines that should contain important fields
    for line_num in key_lines:
        if line_num < len(text_lines):
            print(f"Line {line_num}: {text_lines[line_num-1]}")  # Adjust for 0-indexing
    
    # Sort fields by line_idx to see what the sorted order would be
    sorted_fields = sorted(fields, key=lambda f: getattr(f, 'line_idx', 0))
    print("\n=== FIELDS SORTED BY LINE_IDX ===")
    for i, field in enumerate(sorted_fields[:10]):
        line_idx = field.line_idx if hasattr(field, 'line_idx') else 'unknown'
        print(f"{i+1:2d}. {field.key:35} (line {line_idx:3}) {field.title}")

if __name__ == "__main__":
    debug_field_order()