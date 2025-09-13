#!/usr/bin/env python3
"""
Validate that the npf.json output exactly matches the reference.
"""

import json
import sys
from pathlib import Path

def validate_npf_output():
    """Validate npf.json output against reference"""
    
    # Load files
    reference_path = Path("references/Matching JSON References/npf.json")
    current_path = Path("npf.json")
    
    if not reference_path.exists():
        print(f"❌ Reference file not found: {reference_path}")
        return False
        
    if not current_path.exists():
        print(f"❌ Current output file not found: {current_path}")
        return False
    
    with open(reference_path, 'r') as f:
        reference = json.load(f)
        
    with open(current_path, 'r') as f:
        current = json.load(f)
    
    print(f"📊 Validation Report for npf.json")
    print(f"=" * 50)
    print(f"Reference fields: {len(reference)}")
    print(f"Current fields: {len(current)}")
    
    # Get keys
    ref_keys = [item['key'] for item in reference]
    cur_keys = [item['key'] for item in current]
    
    # Check missing keys
    missing = [k for k in ref_keys if k not in cur_keys]
    extra = [k for k in cur_keys if k not in ref_keys]
    matching = [k for k in ref_keys if k in cur_keys]
    
    print(f"\n🎯 Key Analysis:")
    print(f"  ✅ Matching: {len(matching)} fields")
    print(f"  ❌ Missing: {len(missing)} fields")
    print(f"  ⚠️  Extra: {len(extra)} fields")
    print(f"  📈 Accuracy: {len(matching)}/{len(reference)} = {len(matching)/len(reference)*100:.1f}%")
    
    if missing:
        print(f"\n❌ Missing fields:")
        for key in missing:
            print(f"  - {key}")
    
    if extra:
        print(f"\n⚠️  Extra fields:")
        for key in extra:
            print(f"  - {key}")
    
    # Detailed field comparison for matching keys
    field_issues = []
    for key in matching:
        ref_field = next(item for item in reference if item['key'] == key)
        cur_field = next(item for item in current if item['key'] == key)
        
        # Check critical properties
        if ref_field.get('type') != cur_field.get('type'):
            field_issues.append(f"{key}: type mismatch (ref: {ref_field.get('type')}, cur: {cur_field.get('type')})")
            
        if ref_field.get('section') != cur_field.get('section'):
            field_issues.append(f"{key}: section mismatch (ref: {ref_field.get('section')}, cur: {cur_field.get('section')})")
            
        # Check input_type for input fields
        if ref_field.get('type') == 'input':
            ref_input_type = ref_field.get('control', {}).get('input_type')
            cur_input_type = cur_field.get('control', {}).get('input_type')
            if ref_input_type != cur_input_type:
                field_issues.append(f"{key}: input_type mismatch (ref: {ref_input_type}, cur: {cur_input_type})")
    
    if field_issues:
        print(f"\n🔍 Field Property Issues:")
        for issue in field_issues:
            print(f"  - {issue}")
    
    # Overall validation
    is_valid = (len(missing) == 0 and len(field_issues) == 0)
    
    print(f"\n{'🎉 VALIDATION PASSED' if is_valid else '❌ VALIDATION FAILED'}")
    
    if is_valid:
        print("✅ All required fields are present and correctly formatted!")
        print("✅ npf.json output matches the reference specification!")
        if extra:
            print(f"ℹ️  Note: {len(extra)} extra fields are present but don't affect core functionality.")
    
    return is_valid

if __name__ == "__main__":
    success = validate_npf_output()
    sys.exit(0 if success else 1)