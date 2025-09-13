#!/usr/bin/env python3
"""
Detailed analysis of field positioning and ordering issues
"""

import json

def analyze_field_positions():
    # Load current output
    with open('current_npf_output.json', 'r') as f:
        current = json.load(f)
    
    # Load reference
    with open('pdfs/npf.json', 'r') as f:
        reference = json.load(f)
    
    print("=== DETAILED FIELD ANALYSIS ===")
    print(f"Current: {len(current)} fields")
    print(f"Reference: {len(reference)} fields")
    
    print("\n=== CURRENT OUTPUT FIELD ORDER ===")
    for i, field in enumerate(current):
        print(f"{i+1:2d}. {field['key']:30s} | {field['title']:35s} | {field.get('section', 'Unknown'):25s}")
    
    print("\n=== LOOKING FOR SPECIFIC ISSUES ===")
    
    # Find relationship_to_patient_2 position
    for i, field in enumerate(current):
        if field['key'] == 'relationship_to_patient_2':
            print(f"relationship_to_patient_2 is at position {i+1} (should be around 37)")
            break
    
    # Find insurance company fields in secondary dental plan
    print("\nSecondary Dental Plan fields:")
    for i, field in enumerate(current):
        if field.get('section') == 'Secondary Dental Plan':
            print(f"  {i+1:2d}. {field['key']:30s} | {field['title']}")
    
    # Find insurance_company_2 and phone_2 equivalents
    print("\nLooking for insurance_company_2 and phone_2 equivalents:")
    for i, field in enumerate(current):
        if 'insurance' in field['key'].lower() and '_2' in field['key']:
            print(f"  {i+1:2d}. {field['key']:30s} | {field['title']}")
        if 'phone' in field['key'].lower() and '_2' in field['key']:
            print(f"  {i+1:2d}. {field['key']:30s} | {field['title']}")
    
    # Look for missing fields by checking fields that are in reference but not current
    current_keys = {field['key'] for field in current}
    reference_keys = {field['key'] for field in reference}
    missing_keys = reference_keys - current_keys
    
    print(f"\nMissing fields ({len(missing_keys)}):")
    for key in sorted(missing_keys):
        for ref_field in reference:
            if ref_field['key'] == key:
                print(f"  Missing: {key:30s} | {ref_field['title']}")
                break

if __name__ == "__main__":
    analyze_field_positions()