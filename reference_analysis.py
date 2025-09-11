#!/usr/bin/env python3
"""
Create a focused fix by analyzing the exact patterns in the reference 
and ensuring our script matches them exactly.
"""

import json
from pathlib import Path

def create_reference_pattern_map():
    """Create a mapping of patterns to expected fields based on reference"""
    
    # Load the reference to see exact expected structure
    with open("pdfs/npf.json") as f:
        reference = json.load(f)
    
    # Show first 20 fields of reference for analysis
    print("=== Reference Field Structure (first 20) ===")
    for i, field in enumerate(reference[:20]):
        print(f"{i+1:2d}. {field['key']:25s} | {field['title']:30s} | {field['type']:10s} | {field['section']}")
    
    # Key insight: the reference has a very specific structure
    # Let's see what the first inline field pattern should generate
    print("\n=== Key Pattern Analysis ===")
    
    # From raw text line 5: "First__________________ MI_____ Last_______________________ Nickname_____________"
    # Should generate exactly these 4 fields in this order:
    expected_from_name_line = [
        {"key": "first_name", "title": "First Name", "type": "input", "control": {"input_type": "name"}},
        {"key": "mi", "title": "Middle Initial", "type": "input", "control": {"input_type": "initials"}},
        {"key": "last_name", "title": "Last Name", "type": "input", "control": {"input_type": "name"}},
        {"key": "nickname", "title": "Nickname", "type": "input", "control": {"input_type": "name"}},
    ]
    
    print("Name line should generate:")
    for field in expected_from_name_line:
        print(f"  {field['key']:25s} | {field['title']:30s}")
    
    # From line 7: "Street_________________________________________________________ Apt/Unit/Suite________"
    expected_from_address_line = [
        {"key": "street", "title": "Street", "type": "input", "control": {"input_type": "name"}},
        {"key": "apt_unit_suite", "title": "Apt/Unit/Suite", "type": "input", "control": {"input_type": "name"}},
    ]
    
    print("\nAddress line should generate:")  
    for field in expected_from_address_line:
        print(f"  {field['key']:25s} | {field['title']:30s}")
    
    # Check what sections we should have
    sections_in_reference = {}
    for field in reference:
        section = field['section']
        if section not in sections_in_reference:
            sections_in_reference[section] = 0
        sections_in_reference[section] += 1
    
    print(f"\n=== Reference Sections ===")
    for section, count in sections_in_reference.items():
        print(f"{section}: {count} fields")
    
    return {
        'name_line': expected_from_name_line,
        'address_line': expected_from_address_line,
        'sections': sections_in_reference
    }

def analyze_current_vs_reference():
    """Analyze what our current script produces vs reference"""
    
    with open("improved_npf_output.json") as f:
        current = json.load(f)
    
    with open("pdfs/npf.json") as f:
        reference = json.load(f)
    
    print("=== Current vs Reference Field Comparison ===")
    print(f"Current: {len(current)} fields")
    print(f"Reference: {len(reference)} fields")
    
    # Look at the beginning of both to see the difference
    print("\n=== First 10 fields comparison ===")
    print("Current:")
    for i, field in enumerate(current[:10]):
        print(f"  {i+1:2d}. {field['key']:25s} | {field['title']:30s}")
    
    print("Reference:")  
    for i, field in enumerate(reference[:10]):
        print(f"  {i+1:2d}. {field['key']:25s} | {field['title']:30s}")
    
    # The main issue: we're getting "patient_name", "first", "mi", "last", "nickname"
    # Instead of: "first_name", "mi", "last_name", "nickname"
    print("\n=== Key Issues ===")
    print("1. We're extracting 'Patient Name:' as a separate field - should skip this")
    print("2. Field titles are not normalized: 'First' -> 'First Name', 'MI' -> 'Middle Initial'")
    print("3. We're creating duplicate fields instead of extracting from the main pattern line")
    print("4. Section detection is not working for insurance sections")

def main():
    patterns = create_reference_pattern_map()
    analyze_current_vs_reference()
    
    print("\n=== Fix Strategy ===")
    print("1. Skip 'Patient Name:' line extraction")
    print("2. Focus on the main inline patterns that contain multiple fields") 
    print("3. Use exact field title mappings from reference")
    print("4. Fix section detection for insurance company fields")
    print("5. Prevent duplicate field extraction")

if __name__ == "__main__":
    main()