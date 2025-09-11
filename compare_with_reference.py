#!/usr/bin/env python3
"""
Compare current script output with reference files to identify specific 
issues that need to be fixed.
"""

import json
from pathlib import Path
from collections import defaultdict

def analyze_json_structure(json_data, name):
    """Analyze the structure of a JSON spec"""
    print(f"\n=== Analysis of {name} ===")
    print(f"Total fields: {len(json_data)}")
    
    # Count by section
    sections = defaultdict(int)
    types = defaultdict(int)
    input_types = defaultdict(int)
    
    for field in json_data:
        sections[field.get('section', 'Unknown')] += 1
        types[field.get('type', 'Unknown')] += 1
        
        if field.get('type') == 'input':
            input_types[field.get('control', {}).get('input_type', 'Unknown')] += 1
    
    print(f"Sections: {dict(sections)}")
    print(f"Field types: {dict(types)}")
    print(f"Input types: {dict(input_types)}")
    
    # Show first 10 fields
    print(f"\nFirst 10 fields:")
    for i, field in enumerate(json_data[:10]):
        print(f"  {i+1:2d}. {field.get('key', '?'):20s} | {field.get('title', '?'):25s} | {field.get('type', '?'):10s} | {field.get('section', '?')}")
    
    return {
        'total_fields': len(json_data),
        'sections': dict(sections),
        'types': dict(types),
        'input_types': dict(input_types)
    }

def compare_fields(current, reference):
    """Compare field-by-field differences"""
    print(f"\n=== Field-by-Field Comparison ===")
    
    # Create mappings by key
    current_by_key = {field.get('key'): field for field in current}
    reference_by_key = {field.get('key'): field for field in reference}
    
    all_keys = set(current_by_key.keys()) | set(reference_by_key.keys())
    
    print(f"Keys only in current: {set(current_by_key.keys()) - set(reference_by_key.keys())}")
    print(f"Keys only in reference: {set(reference_by_key.keys()) - set(current_by_key.keys())}")
    
    # Compare matching keys
    matching_keys = set(current_by_key.keys()) & set(reference_by_key.keys())
    print(f"\nMatching keys: {len(matching_keys)}")
    
    differences = []
    for key in sorted(matching_keys):
        current_field = current_by_key[key]
        reference_field = reference_by_key[key]
        
        diffs = []
        for attr in ['title', 'section', 'type', 'optional']:
            if current_field.get(attr) != reference_field.get(attr):
                diffs.append(f"{attr}: {current_field.get(attr)} -> {reference_field.get(attr)}")
        
        # Compare control
        current_control = current_field.get('control', {})
        reference_control = reference_field.get('control', {})
        
        if current_control != reference_control:
            diffs.append(f"control: {current_control} -> {reference_control}")
        
        if diffs:
            differences.append((key, diffs))
    
    print(f"\nFields with differences: {len(differences)}")
    for key, diffs in differences[:10]:  # Show first 10
        print(f"  {key}: {'; '.join(diffs)}")

def main():
    # Load files
    current_path = Path("improved_npf_output.json")
    reference_path = Path("pdfs/npf.json")
    
    if not current_path.exists():
        print(f"Current output file not found: {current_path}")
        return
    
    if not reference_path.exists():
        print(f"Reference file not found: {reference_path}")
        return
    
    with open(current_path) as f:
        current = json.load(f)
    
    with open(reference_path) as f:
        reference = json.load(f)
    
    # Analyze both
    current_stats = analyze_json_structure(current, "Current Output")
    reference_stats = analyze_json_structure(reference, "Reference")
    
    # Compare
    compare_fields(current, reference)
    
    # Summary
    print(f"\n=== Summary ===")
    print(f"Current has {current_stats['total_fields']} fields, reference has {reference_stats['total_fields']} fields")
    print(f"Section count difference: {len(current_stats['sections'])} vs {len(reference_stats['sections'])}")
    print(f"Type distribution matches: {current_stats['types'] == reference_stats['types']}")

if __name__ == "__main__":
    main()