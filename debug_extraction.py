#!/usr/bin/env python3
"""
Debug the field extraction to see exactly where "Patient Name" is coming from.
"""

import json
from pathlib import Path
from docling.document_converter import DocumentConverter
from docling.datamodel.pipeline_options import PdfPipelineOptions

def debug_extraction():
    """Debug where Patient Name field is coming from"""
    
    # Extract raw text
    pipeline_options = PdfPipelineOptions()
    pipeline_options.do_ocr = True
    pipeline_options.do_table_structure = True
    pipeline_options.images_scale = 2.0
    
    converter = DocumentConverter()
    result = converter.convert("pdfs/npf.pdf")
    full_text = result.document.export_to_text()
    lines = [line.strip() for line in full_text.split('\n') if line.strip()]
    
    print("=== Debug Field Extraction ===")
    
    # Look for any line that might be creating "Patient Name" field
    possible_lines = []
    for i, line in enumerate(lines):
        if 'patient' in line.lower() and 'name' in line.lower():
            possible_lines.append((i+1, line))
    
    print("Lines containing 'patient' and 'name':")
    for line_num, line in possible_lines:
        print(f"  {line_num:3d}: {line}")
    
    # Load the current problematic output
    with open("improved4_npf_output.json") as f:
        current = json.load(f)
    
    # Find the "patient_name" field
    patient_name_field = None
    for i, field in enumerate(current):
        if field.get('key') == 'patient_name':
            patient_name_field = (i, field)
            break
    
    if patient_name_field:
        idx, field = patient_name_field
        print(f"\nFound 'patient_name' field at index {idx}:")
        print(f"  Key: {field.get('key')}")
        print(f"  Title: {field.get('title')}")
        print(f"  Section: {field.get('section')}")
        print(f"  Type: {field.get('type')}")
        
        # The issue: this field should not exist at all
        print(f"\nThis field should not exist. It's likely extracted from line 7: 'Patient Name:'")
        print(f"We need to prevent this extraction entirely.")
    
    # Check the first few fields vs reference
    with open("pdfs/npf.json") as f:
        reference = json.load(f)
    
    print(f"\n=== First 5 fields comparison ===")
    print("Current:")
    for i, field in enumerate(current[:5]):
        print(f"  {i+1}. {field['key']:20s} | {field['title']}")
    
    print("Reference:")
    for i, field in enumerate(reference[:5]):
        print(f"  {i+1}. {field['key']:20s} | {field['title']}")

if __name__ == "__main__":
    debug_extraction()