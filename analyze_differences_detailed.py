#!/usr/bin/env python3
"""
Detailed analysis of differences between current output and reference for npf.json
"""
import json
from pathlib import Path

def analyze_npf_differences():
    """Analyze differences between current npf output and reference"""
    
    # Load files
    try:
        with open('npf_current_output.json', 'r') as f:
            current = json.load(f)
    except FileNotFoundError:
        with open('output_current/npf.json', 'r') as f:
            current = json.load(f)
    
    with open('references/Matching JSON References/npf.json', 'r') as f:
        reference = json.load(f)
    
    print(f"=== NPF.JSON ANALYSIS ===")
    print(f"Current output: {len(current)} fields")
    print(f"Reference: {len(reference)} fields")
    print(f"Difference: {len(reference) - len(current)} fields missing")
    print()
    
    # Analyze field keys
    current_keys = {field['key'] for field in current}
    reference_keys = {field['key'] for field in reference}
    
    missing_keys = reference_keys - current_keys
    extra_keys = current_keys - reference_keys
    common_keys = current_keys & reference_keys
    
    print(f"=== KEY ANALYSIS ===")
    print(f"Common keys: {len(common_keys)}")
    print(f"Missing keys: {len(missing_keys)}")
    print(f"Extra keys: {len(extra_keys)}")
    print()
    
    if missing_keys:
        print("MISSING KEYS:")
        for key in sorted(missing_keys):
            ref_field = next(f for f in reference if f['key'] == key)
            print(f"  - {key} ({ref_field['type']}) '{ref_field['title']}' in section '{ref_field['section']}'")
        print()
    
    if extra_keys:
        print("EXTRA KEYS:")
        for key in sorted(extra_keys):
            curr_field = next(f for f in current if f['key'] == key)
            print(f"  - {key} ({curr_field['type']}) '{curr_field['title']}' in section '{curr_field['section']}'")
        print()
    
    # Analyze sections
    current_sections = {field['section'] for field in current}
    reference_sections = {field['section'] for field in reference}
    
    print(f"=== SECTION ANALYSIS ===")
    print("Current sections:", sorted(current_sections))
    print("Reference sections:", sorted(reference_sections))
    print("Missing sections:", sorted(reference_sections - current_sections))
    print("Extra sections:", sorted(current_sections - reference_sections))
    print()
    
    # Analyze field order for first 10 fields
    print("=== FIELD ORDER COMPARISON (first 10) ===")
    for i in range(min(10, len(current), len(reference))):
        curr = current[i]
        ref = reference[i]
        match = "✓" if curr['key'] == ref['key'] else "✗"
        print(f"{i+1:2d}. {match} Current: {curr['key']:20} | Reference: {ref['key']:20}")
    print()
    
    # Analyze specific problematic patterns
    print("=== SPECIFIC ISSUES ===")
    
    # Check for duplicate patient_name vs first_name/last_name issue
    has_patient_name = any(f['key'] == 'patient_name' for f in current)
    has_first_name = any(f['key'] == 'first_name' for f in current)
    if has_patient_name and has_first_name:
        print("⚠ Issue: Both 'patient_name' and 'first_name' exist - likely over-extraction")
    
    # Check middle initial naming
    has_mi = any(f['key'] == 'mi' for f in current)
    has_middle_initial = any(f['key'] == 'middle_initial' for f in current)
    if has_middle_initial and not has_mi:
        print("⚠ Issue: Using 'middle_initial' instead of 'mi' key")
    
    # Check for missing fields that should always be present
    critical_missing = []
    for key in ['mi', 'nickname', 'apt_unit_suite']:
        if key not in current_keys:
            critical_missing.append(key)
    
    if critical_missing:
        print(f"⚠ Critical missing fields: {critical_missing}")
    
    # Analyze control structure differences for common fields
    print("\n=== CONTROL STRUCTURE ANALYSIS ===")
    for key in list(common_keys)[:5]:  # Check first 5 common keys
        curr_field = next(f for f in current if f['key'] == key)
        ref_field = next(f for f in reference if f['key'] == key)
        
        if curr_field['control'] != ref_field['control']:
            print(f"Control difference for '{key}':")
            print(f"  Current: {curr_field['control']}")
            print(f"  Reference: {ref_field['control']}")
    
    return {
        'missing_keys': missing_keys,
        'extra_keys': extra_keys,
        'common_keys': common_keys,
        'current_sections': current_sections,
        'reference_sections': reference_sections
    }

if __name__ == "__main__":
    analyze_npf_differences()