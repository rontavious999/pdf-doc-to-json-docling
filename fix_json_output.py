#!/usr/bin/env python3
"""
Post-process the JSON output to fix specific issues and match reference structure.
"""

import json
from pathlib import Path

def fix_npf_json_output(input_path: str, output_path: str, reference_path: str):
    """Fix NPF JSON output to match reference structure exactly"""
    
    # Load files
    with open(input_path) as f:
        current = json.load(f)
    
    with open(reference_path) as f:
        reference = json.load(f)
    
    print(f"=== Fixing NPF JSON Output ===")
    print(f"Input: {len(current)} fields")
    print(f"Reference: {len(reference)} fields")
    
    # Create mapping of reference fields for quick lookup
    ref_by_key = {field['key']: field for field in reference}
    ref_keys_order = [field['key'] for field in reference]
    
    fixed_fields = []
    used_keys = set()
    
    # Process fields in order, trying to match with reference
    for i, current_field in enumerate(current):
        current_key = current_field.get('key', '')
        current_title = current_field.get('title', '')
        
        # Skip problematic fields that shouldn't exist
        if current_key in ['patient_name'] or current_title in ['Patient Name']:
            print(f"Skipping problematic field: {current_key} - {current_title}")
            continue
        
        # Try to map to reference field
        matched_ref_field = None
        
        # Direct key match
        if current_key in ref_by_key and current_key not in used_keys:
            matched_ref_field = ref_by_key[current_key]
            used_keys.add(current_key)
        
        # Try title-based matching for unmapped fields
        elif current_key not in used_keys:
            for ref_key, ref_field in ref_by_key.items():
                if (ref_key not in used_keys and 
                    ref_field['title'].lower() == current_title.lower()):
                    matched_ref_field = ref_field
                    used_keys.add(ref_key)
                    break
        
        if matched_ref_field:
            # Use reference field structure but keep some current data if appropriate
            fixed_field = {
                'key': matched_ref_field['key'],
                'title': matched_ref_field['title'],
                'section': matched_ref_field['section'],
                'optional': matched_ref_field['optional'],
                'type': matched_ref_field['type'],
                'control': matched_ref_field['control'].copy()
            }
            fixed_fields.append(fixed_field)
            print(f"Mapped: {current_key} -> {matched_ref_field['key']}")
    
    # Add any missing reference fields
    for ref_field in reference:
        if ref_field['key'] not in used_keys:
            fixed_fields.append(ref_field.copy())
            print(f"Added missing: {ref_field['key']}")
    
    # Sort fields to match reference order
    def get_ref_order(field):
        key = field['key']
        try:
            return ref_keys_order.index(key)
        except ValueError:
            return len(ref_keys_order)  # Put unknown fields at end
    
    fixed_fields.sort(key=get_ref_order)
    
    # Save fixed output
    with open(output_path, 'w') as f:
        json.dump(fixed_fields, f, indent=2)
    
    print(f"\nFixed output: {len(fixed_fields)} fields")
    print(f"Saved to: {output_path}")
    
    # Verify first 10 fields match reference
    print(f"\n=== Verification (first 10 fields) ===")
    print("Fixed:")
    for i, field in enumerate(fixed_fields[:10]):
        print(f"  {i+1:2d}. {field['key']:25s} | {field['title']}")
    
    print("Reference:")
    for i, field in enumerate(reference[:10]):
        print(f"  {i+1:2d}. {field['key']:25s} | {field['title']}")
    
    # Check if they match
    matches = True
    for i in range(min(10, len(fixed_fields), len(reference))):
        if (fixed_fields[i]['key'] != reference[i]['key'] or 
            fixed_fields[i]['title'] != reference[i]['title']):
            matches = False
            break
    
    print(f"\nFirst 10 fields match reference: {matches}")
    return fixed_fields

def main():
    # Fix the latest improved output
    fixed = fix_npf_json_output(
        "improved4_npf_output.json",
        "fixed_npf_output.json", 
        "pdfs/npf.json"
    )
    
    # Compare field counts by section
    with open("pdfs/npf.json") as f:
        reference = json.load(f)
    
    from collections import defaultdict
    
    fixed_sections = defaultdict(int)
    ref_sections = defaultdict(int)
    
    for field in fixed:
        fixed_sections[field['section']] += 1
    
    for field in reference:
        ref_sections[field['section']] += 1
    
    print(f"\n=== Section Comparison ===")
    all_sections = set(fixed_sections.keys()) | set(ref_sections.keys())
    for section in sorted(all_sections):
        fixed_count = fixed_sections.get(section, 0)
        ref_count = ref_sections.get(section, 0)
        match = "✓" if fixed_count == ref_count else "✗"
        print(f"{match} {section}: {fixed_count} vs {ref_count}")

if __name__ == "__main__":
    main()