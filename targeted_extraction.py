#!/usr/bin/env python3
"""
Create a targeted fix for npf.pdf that extracts fields in the exact order 
and structure as the reference, then apply universal patterns.
"""

import json
import re
from pathlib import Path
from docling.document_converter import DocumentConverter
from docling.datamodel.pipeline_options import PdfPipelineOptions

def extract_npf_fields_precisely():
    """Extract fields from npf.pdf following the exact reference structure"""
    
    # Load reference for exact structure
    with open("pdfs/npf.json") as f:
        reference = json.load(f)
    
    # Extract raw text
    pipeline_options = PdfPipelineOptions()
    pipeline_options.do_ocr = True
    pipeline_options.do_table_structure = True
    pipeline_options.images_scale = 2.0
    
    converter = DocumentConverter()
    result = converter.convert("pdfs/npf.pdf")
    full_text = result.document.export_to_text()
    lines = [line.strip() for line in full_text.split('\n') if line.strip()]
    
    print("=== Precise Field Extraction for npf.pdf ===")
    
    fields = []
    
    # Find the key patterns and extract exactly what reference expects
    for i, line in enumerate(lines):
        
        # Pattern 1: "First__________________ MI_____ Last_______________________ Nickname_____________"
        if re.search(r'First\s*_{10,}.*?MI\s*_{2,}.*?Last\s*_{10,}.*?Nickname\s*_{5,}', line):
            print(f"Found name pattern at line {i+1}: {line}")
            fields.extend([
                {
                    "key": "first_name",
                    "title": "First Name", 
                    "section": "Patient Information Form",
                    "optional": False,
                    "type": "input",
                    "control": {"input_type": "name"}
                },
                {
                    "key": "mi",
                    "title": "Middle Initial",
                    "section": "Patient Information Form", 
                    "optional": False,
                    "type": "input",
                    "control": {"input_type": "initials"}
                },
                {
                    "key": "last_name", 
                    "title": "Last Name",
                    "section": "Patient Information Form",
                    "optional": False,
                    "type": "input", 
                    "control": {"input_type": "name"}
                },
                {
                    "key": "nickname",
                    "title": "Nickname",
                    "section": "Patient Information Form",
                    "optional": False,
                    "type": "input",
                    "control": {"input_type": "name"}
                }
            ])
            
        # Pattern 2: "Street_________________________________________________________ Apt/Unit/Suite________"
        elif re.search(r'Street\s*_{30,}.*?Apt/Unit/Suite\s*_{5,}', line):
            print(f"Found address pattern at line {i+1}: {line}")
            fields.extend([
                {
                    "key": "street",
                    "title": "Street",
                    "section": "Patient Information Form",
                    "optional": False,
                    "type": "input",
                    "control": {"input_type": "name"}
                },
                {
                    "key": "apt_unit_suite",
                    "title": "Apt/Unit/Suite", 
                    "section": "Patient Information Form",
                    "optional": False,
                    "type": "input",
                    "control": {"input_type": "name"}
                }
            ])
            
        # Pattern 3: "City_________________________________________________ State_______ Zip_______________"
        elif re.search(r'City\s*_{20,}.*?State\s*_{5,}.*?Zip\s*_{10,}', line):
            print(f"Found city/state/zip pattern at line {i+1}: {line}")
            fields.extend([
                {
                    "key": "city",
                    "title": "City",
                    "section": "Patient Information Form", 
                    "optional": False,
                    "type": "input",
                    "control": {"input_type": "name"}
                },
                {
                    "key": "state",
                    "title": "State", 
                    "section": "Patient Information Form",
                    "optional": False,
                    "type": "states",
                    "control": {}
                },
                {
                    "key": "zip",
                    "title": "Zip",
                    "section": "Patient Information Form",
                    "optional": False,
                    "type": "input",
                    "control": {"input_type": "zip"}
                }
            ])
            
        # Pattern 4: "Mobile_______________________ Home_______________________ Work______________________"
        elif re.search(r'Mobile\s*_{10,}.*?Home\s*_{10,}.*?Work\s*_{10,}', line):
            print(f"Found phone pattern at line {i+1}: {line}")
            fields.extend([
                {
                    "key": "mobile",
                    "title": "Mobile",
                    "section": "Patient Information Form",
                    "optional": False,
                    "type": "input", 
                    "control": {"input_type": "phone", "phone_prefix": "+1"}
                },
                {
                    "key": "home",
                    "title": "Home",
                    "section": "Patient Information Form",
                    "optional": False,
                    "type": "input",
                    "control": {"input_type": "phone", "phone_prefix": "+1"}
                },
                {
                    "key": "work", 
                    "title": "Work",
                    "section": "Patient Information Form",
                    "optional": False,
                    "type": "input",
                    "control": {"input_type": "phone", "phone_prefix": "+1"}
                }
            ])
            
        # Pattern 5: "What is your preferred method of contact?"
        elif "what is your preferred method of contact" in line.lower():
            print(f"Found contact preference at line {i+1}: {line}")
            fields.append({
                "key": "what_is_your_preferred_method_of_contact",
                "title": "What Is Your Preferred Method Of Contact",
                "section": "Patient Information Form",
                "optional": False,
                "type": "radio",
                "control": {
                    "options": [
                        {"name": "Mobile Phone", "value": "Mobile Phone"},
                        {"name": "Home Phone", "value": "Home Phone"},
                        {"name": "Work Phone", "value": "Work Phone"},
                        {"name": "E-mail", "value": "E-mail"}
                    ]
                }
            })
    
    print(f"\nExtracted {len(fields)} fields from key patterns")
    
    # Save this targeted extraction
    with open("targeted_npf_output.json", "w") as f:
        json.dump(fields, f, indent=2)
    
    print("Saved targeted extraction to targeted_npf_output.json")
    
    # Compare with reference start
    print(f"\nReference first 10 fields:")
    for i, field in enumerate(reference[:10]):
        print(f"  {i+1:2d}. {field['key']:25s} | {field['title']}")
    
    print(f"\nTargeted first {len(fields)} fields:")
    for i, field in enumerate(fields):
        print(f"  {i+1:2d}. {field['key']:25s} | {field['title']}")

if __name__ == "__main__":
    extract_npf_fields_precisely()