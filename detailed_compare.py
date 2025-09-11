#!/usr/bin/env python3

import json
from pathlib import Path

def compare_detailed():
    # Load both files
    with open('references/Matching JSON References/npf.json') as f:
        reference = json.load(f)
    
    with open('improved7_npf_output.json') as f:
        current = json.load(f)
    
    print(f"Reference: {len(reference)} fields")
    print(f"Current: {len(current)} fields")
    print(f"Difference: {len(reference) - len(current)} fields\n")
    
    # Create lookups
    ref_by_key = {field['key']: field for field in reference}
    current_by_key = {field['key']: field for field in current}
    
    # Find missing fields
    missing_keys = set(ref_by_key.keys()) - set(current_by_key.keys())
    extra_keys = set(current_by_key.keys()) - set(ref_by_key.keys())
    
    print(f"=== MISSING FIELDS ({len(missing_keys)}) ===")
    for key in sorted(missing_keys):
        field = ref_by_key[key]
        print(f"  {key}: {field['title']} ({field['type']}) - Section: {field['section']}")
    
    print(f"\n=== EXTRA FIELDS ({len(extra_keys)}) ===")
    for key in sorted(extra_keys):
        field = current_by_key[key]
        print(f"  {key}: {field['title']} ({field['type']}) - Section: {field['section']}")
    
    # Check section distribution
    print(f"\n=== SECTION DISTRIBUTION ===")
    ref_sections = {}
    curr_sections = {}
    
    for field in reference:
        section = field['section']
        ref_sections[section] = ref_sections.get(section, 0) + 1
    
    for field in current:
        section = field['section']
        curr_sections[section] = curr_sections.get(section, 0) + 1
    
    all_sections = set(ref_sections.keys()) | set(curr_sections.keys())
    for section in sorted(all_sections):
        ref_count = ref_sections.get(section, 0)
        curr_count = curr_sections.get(section, 0)
        diff = curr_count - ref_count
        print(f"  {section}: Ref={ref_count}, Curr={curr_count}, Diff={diff:+d}")
    
    # Check text fields specifically
    print(f"\n=== TEXT FIELDS ===")
    ref_text_fields = [f for f in reference if f['type'] == 'text']
    curr_text_fields = [f for f in current if f['type'] == 'text']
    
    print(f"Reference text fields: {len(ref_text_fields)}")
    for field in ref_text_fields:
        print(f"  {field['key']}: Section={field['section']}")
    
    print(f"Current text fields: {len(curr_text_fields)}")
    for field in curr_text_fields:
        print(f"  {field['key']}: Section={field['section']}")

if __name__ == "__main__":
    compare_detailed()