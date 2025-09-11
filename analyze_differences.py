#!/usr/bin/env python3
"""
Analyze differences between current output and reference npf.json
"""
import json
from typing import Dict, List, Set

def load_json(file_path: str) -> List[Dict]:
    """Load JSON file and return list of fields"""
    with open(file_path, 'r') as f:
        return json.load(f)

def extract_field_info(fields: List[Dict]) -> List[Dict]:
    """Extract key information from fields"""
    info = []
    for field in fields:
        info.append({
            'key': field.get('key', ''),
            'title': field.get('title', ''),
            'type': field.get('type', ''),
            'section': field.get('section', ''),
            'optional': field.get('optional', False),  # Default to False per Modento schema
            'input_type': field.get('control', {}).get('input_type', '')
        })
    return info

def compare_fields(ref_fields: List[Dict], current_fields: List[Dict]):
    """Compare reference and current fields"""
    ref_info = extract_field_info(ref_fields)
    current_info = extract_field_info(current_fields)
    
    ref_keys = {f['key'] for f in ref_info}
    current_keys = {f['key'] for f in current_info}
    
    missing_keys = ref_keys - current_keys
    extra_keys = current_keys - ref_keys
    common_keys = ref_keys & current_keys
    
    print(f"Reference fields: {len(ref_fields)}")
    print(f"Current fields: {len(current_fields)}")
    print(f"Missing fields: {len(missing_keys)}")
    print(f"Extra fields: {len(extra_keys)}")
    print(f"Common fields: {len(common_keys)}")
    print()
    
    # Find missing fields
    if missing_keys:
        print("MISSING FIELDS:")
        missing_fields = [f for f in ref_info if f['key'] in missing_keys]
        for field in missing_fields:
            print(f"  - {field['key']}: {field['title']} ({field['type']}) in {field['section']}")
        print()
    
    # Find extra fields
    if extra_keys:
        print("EXTRA FIELDS:")
        extra_fields = [f for f in current_info if f['key'] in extra_keys]
        for field in extra_fields:
            print(f"  + {field['key']}: {field['title']} ({field['type']}) in {field['section']}")
        print()
    
    # Check differences in common fields
    print("FIELD DIFFERENCES:")
    ref_by_key = {f['key']: f for f in ref_info}
    current_by_key = {f['key']: f for f in current_info}
    
    different_fields = 0
    for key in common_keys:
        ref_field = ref_by_key[key]
        current_field = current_by_key[key]
        
        differences = []
        for attr in ['title', 'type', 'section', 'optional', 'input_type']:
            if ref_field[attr] != current_field[attr]:
                differences.append(f"{attr}: '{ref_field[attr]}' vs '{current_field[attr]}'")
        
        if differences:
            different_fields += 1
            print(f"  {key}: {', '.join(differences)}")
    
    if different_fields == 0:
        print("  No differences in common fields")
    
    print(f"\nSummary: {different_fields} fields have differences in attributes")

def analyze_sections(ref_fields: List[Dict], current_fields: List[Dict]):
    """Analyze section distribution"""
    ref_sections = {}
    current_sections = {}
    
    for field in ref_fields:
        section = field.get('section', 'Unknown')
        ref_sections[section] = ref_sections.get(section, 0) + 1
    
    for field in current_fields:
        section = field.get('section', 'Unknown')
        current_sections[section] = current_sections.get(section, 0) + 1
    
    print("\nSECTION DISTRIBUTION:")
    all_sections = set(ref_sections.keys()) | set(current_sections.keys())
    
    for section in sorted(all_sections):
        ref_count = ref_sections.get(section, 0)
        current_count = current_sections.get(section, 0)
        status = "✓" if ref_count == current_count else "✗"
        print(f"  {status} {section}: {current_count}/{ref_count}")

def main():
    print("=== NPF.JSON ANALYSIS ===\n")
    
    ref_fields = load_json('references/Matching JSON References/npf.json')
    current_fields = load_json('npf_current_output.json')
    
    compare_fields(ref_fields, current_fields)
    analyze_sections(ref_fields, current_fields)

if __name__ == "__main__":
    main()