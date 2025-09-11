#!/usr/bin/env python3
"""
Debug script to see what text is being extracted from npf.pdf
"""
import sys
from pathlib import Path
sys.path.append('.')

from pdf_to_json_converter import PDFFormFieldExtractor

def main():
    extractor = PDFFormFieldExtractor()
    pdf_path = Path("pdfs/npf.pdf")
    
    print("=== EXTRACTED TEXT LINES ===")
    text_lines, pipeline_info = extractor.extract_text_from_pdf(pdf_path)
    
    print(f"Total lines extracted: {len(text_lines)}")
    print("\nFirst 20 lines:")
    for i, line in enumerate(text_lines[:20]):
        print(f"{i+1:2d}: {repr(line)}")
    
    print("\n=== LOOKING FOR DATE PATTERNS ===")
    date_patterns = []
    for i, line in enumerate(text_lines):
        line_lower = line.lower()
        if any(keyword in line_lower for keyword in ['date', 'today']):
            date_patterns.append((i+1, line))
    
    print(f"Found {len(date_patterns)} lines with date/today:")
    for line_num, line in date_patterns:
        print(f"  {line_num}: {repr(line)}")
    
    print("\n=== LOOKING FOR FIELD PATTERNS ===")
    field_patterns = []
    for i, line in enumerate(text_lines):
        if '____' in line or '_____' in line:
            field_patterns.append((i+1, line))
    
    print(f"Found {len(field_patterns)} lines with underscores (potential fields):")
    for line_num, line in field_patterns[:10]:  # Show first 10
        print(f"  {line_num}: {repr(line)}")

if __name__ == "__main__":
    main()