#!/usr/bin/env python3
"""
Debug specific field parsing logic
"""
import json
from pathlib import Path
from pdf_to_json_converter import PDFFormFieldExtractor

def debug_field_parsing():
    """Debug field parsing logic for the problematic lines"""
    
    extractor = PDFFormFieldExtractor()
    
    # Test specific lines from the extraction
    test_lines = [
        "Patient Name:",
        "First__________________ MI_____ Last_______________________ Nickname_____________",
        "Street_________________________________________________________ Apt/Unit/Suite________",
        "City_________________________________________________ State_______ Zip_______________",
        "Middle Initial",
        "SSN"
    ]
    
    print("=== TESTING INLINE FIELD PARSING ===")
    for line in test_lines:
        fields = extractor.parse_inline_fields(line)
        print(f"Line: {line}")
        print(f"Fields found: {fields}")
        print()
    
    print("=== TESTING FIELD NORMALIZATION ===")
    test_names = ["Middle Initial", "MI", "mi", "First Name", "Patient Name"]
    for name in test_names:
        normalized = extractor.normalize_field_name(name)
        print(f"{name} -> {normalized}")

if __name__ == "__main__":
    debug_field_parsing()