#!/usr/bin/env python3
"""
Create exact field mapping by analyzing the raw text patterns and 
matching them to the reference structure.
"""

import json
from pathlib import Path
import re

def create_field_mapping_from_reference():
    """Create field mapping by analyzing reference and raw text"""
    
    # Load reference to understand expected structure
    with open("pdfs/npf.json") as f:
        reference = json.load(f)
    
    # Load raw text analysis
    with open("text_analysis/npf_raw_text.txt") as f:
        raw_text = f.read()
    
    lines = [line.strip() for line in raw_text.split('\n') if line.strip()]
    
    print("=== Field Mapping Analysis ===")
    print(f"Reference has {len(reference)} fields")
    print(f"Raw text has {len(lines)} lines")
    
    # Map key lines from raw text to expected fields
    expected_mappings = []
    
    # Key patterns we need to extract correctly
    patterns = {
        # Line 5: "First__________________ MI_____ Last_______________________ Nickname_____________"
        "First__________________ MI_____ Last_______________________ Nickname_____________": [
            ("first_name", "First Name", "input", {"input_type": "name"}),
            ("mi", "Middle Initial", "input", {"input_type": "initials"}), 
            ("last_name", "Last Name", "input", {"input_type": "name"}),
            ("nickname", "Nickname", "input", {"input_type": "name"})
        ],
        
        # Line 7: "Street_________________________________________________________ Apt/Unit/Suite________"
        "Street_________________________________________________________ Apt/Unit/Suite________": [
            ("street", "Street", "input", {"input_type": "name"}),
            ("apt_unit_suite", "Apt/Unit/Suite", "input", {"input_type": "name"})
        ],
        
        # Line 8: "City_________________________________________________ State_______ Zip_______________"  
        "City_________________________________________________ State_______ Zip_______________": [
            ("city", "City", "input", {"input_type": "name"}),
            ("state", "State", "states", {}),
            ("zip", "Zip", "input", {"input_type": "zip"})
        ],
        
        # Line 10: "Mobile_______________________ Home_______________________ Work______________________"
        "Mobile_______________________ Home_______________________ Work______________________": [
            ("mobile", "Mobile", "input", {"input_type": "phone", "phone_prefix": "+1"}),
            ("home", "Home", "input", {"input_type": "phone", "phone_prefix": "+1"}),
            ("work", "Work", "input", {"input_type": "phone", "phone_prefix": "+1"})
        ],
        
        # Radio button patterns
        "What is your preferred method of contact?": [
            ("what_is_your_preferred_method_of_contact", "What Is Your Preferred Method Of Contact", "radio", {
                "options": [
                    {"name": "Mobile Phone", "value": "Mobile Phone"},
                    {"name": "Home Phone", "value": "Home Phone"},
                    {"name": "Work Phone", "value": "Work Phone"},
                    {"name": "E-mail", "value": "E-mail"}
                ]
            })
        ],
        
        "Sex": [
            ("sex", "Sex", "radio", {
                "options": [
                    {"name": "Male", "value": "male"},
                    {"name": "Female", "value": "female"}
                ]
            })
        ],
        
        "Marital Status": [
            ("marital_status", "Marital Status", "radio", {
                "options": [
                    {"name": "Married", "value": "Married"},
                    {"name": "Single", "value": "Single"},
                    {"name": "Divorced", "value": "Divorced"},
                    {"name": "Separated", "value": "Separated"},
                    {"name": "Widowed", "value": "Widowed"}
                ]
            })
        ]
    }
    
    print("\n=== Pattern Mappings ===")
    for pattern, fields in patterns.items():
        print(f"\nPattern: {pattern}")
        for key, title, field_type, control in fields:
            print(f"  -> {key}: {title} ({field_type})")
    
    # Find these patterns in the raw text
    print("\n=== Pattern Matches in Raw Text ===")
    for pattern in patterns.keys():
        for i, line in enumerate(lines):
            if pattern in line or line.strip() == pattern.strip():
                print(f"Line {i+1}: {line}")
                break
        else:
            # Try fuzzy matching for similar patterns
            for i, line in enumerate(lines):
                if len(set(pattern.split()) & set(line.split())) > 2:
                    print(f"Similar Line {i+1}: {line}")
                    break
    
    return patterns

def analyze_section_structure():
    """Analyze section structure from raw text"""
    
    with open("text_analysis/npf_raw_text.txt") as f:
        raw_text = f.read()
    
    lines = [line.strip() for line in raw_text.split('\n') if line.strip()]
    
    # Find section headers
    sections = []
    for i, line in enumerate(lines):
        if line.startswith('##'):
            sections.append((i+1, line.replace('##', '').strip()))
    
    print("\n=== Section Structure ===")
    for line_num, section in sections:
        print(f"Line {line_num}: {section}")
    
    # Map to reference sections
    reference_sections = {
        "Patient Information Form": "Patient Information Form",
        "FOR CHILDREN/MINORS ONLY": "FOR CHILDREN/MINORS ONLY", 
        "Dental Benefit Plan Information Primary Dental Plan": "Primary Dental Plan",
        "Secondary Dental Plan": "Secondary Dental Plan"
    }
    
    print("\n=== Section Mapping ===")
    for raw_section, ref_section in reference_sections.items():
        print(f"{raw_section} -> {ref_section}")
    
    return reference_sections

def main():
    patterns = create_field_mapping_from_reference()
    sections = analyze_section_structure()
    
    print("\n=== Summary ===")
    print("The key issues to fix in the script:")
    print("1. Field name normalization: 'First' -> 'First Name', 'MI' -> 'Middle Initial'")
    print("2. Section name mapping for dental plan sections")
    print("3. Proper radio button option extraction")
    print("4. Avoid duplicate field extraction")
    print("5. Use exact titles and keys from reference")

if __name__ == "__main__":
    main()