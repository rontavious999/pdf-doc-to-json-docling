#!/usr/bin/env python3
"""
Compare current output with reference to identify missing fields and differences.
"""

import json
from pathlib import Path

def compare_outputs():
    # Load both files
    with open('npf_reference_formatted.json') as f:
        reference = json.load(f)
    
    with open('npf_test_output.json') as f:
        current = json.load(f)
    
    print(f"Reference has {len(reference)} fields")
    print(f"Current has {len(current)} fields")
    print(f"Missing: {len(reference) - len(current)} fields\n")
    
    # Create sets of keys for comparison
    ref_keys = set(field['key'] for field in reference)
    current_keys = set(field['key'] for field in current)
    
    missing_keys = ref_keys - current_keys
    extra_keys = current_keys - ref_keys
    common_keys = ref_keys & current_keys
    
    print(f"=== MISSING FIELDS ({len(missing_keys)}) ===")
    ref_by_key = {field['key']: field for field in reference}
    for key in sorted(missing_keys):
        field = ref_by_key[key]
        print(f"  {key}: {field['title']} ({field['type']}) - Section: {field['section']}")
    
    print(f"\n=== EXTRA FIELDS ({len(extra_keys)}) ===")
    current_by_key = {field['key']: field for field in current}
    for key in sorted(extra_keys):
        field = current_by_key[key]
        print(f"  {key}: {field['title']} ({field['type']}) - Section: {field['section']}")
    
    print(f"\n=== FIELD DIFFERENCES ===")
    differences = 0
    for key in sorted(common_keys):
        ref_field = ref_by_key[key]
        current_field = current_by_key[key]
        
        diffs = []
        if ref_field['title'] != current_field['title']:
            diffs.append(f"title: '{ref_field['title']}' vs '{current_field['title']}'")
        if ref_field['section'] != current_field['section']:
            diffs.append(f"section: '{ref_field['section']}' vs '{current_field['section']}'")
        if ref_field['type'] != current_field['type']:
            diffs.append(f"type: '{ref_field['type']}' vs '{current_field['type']}'")
        if ref_field.get('optional', False) != current_field.get('optional', False):
            diffs.append(f"optional: {ref_field.get('optional', False)} vs {current_field.get('optional', False)}")
        
        if diffs:
            differences += 1
            print(f"  {key}: {' | '.join(diffs)}")
    
    print(f"\nTotal differences in common fields: {differences}")
    
    # Section analysis
    print(f"\n=== SECTION ANALYSIS ===")
    ref_sections = {}
    for field in reference:
        section = field['section']
        if section not in ref_sections:
            ref_sections[section] = []
        ref_sections[section].append(field['key'])
    
    current_sections = {}
    for field in current:
        section = field['section']
        if section not in current_sections:
            current_sections[section] = []
        current_sections[section].append(field['key'])
    
    print("Reference sections:")
    for section, keys in ref_sections.items():
        print(f"  {section}: {len(keys)} fields")
    
    print("\nCurrent sections:")
    for section, keys in current_sections.items():
        print(f"  {section}: {len(keys)} fields")

if __name__ == "__main__":
    compare_outputs()