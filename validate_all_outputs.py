#!/usr/bin/env python3
"""
Comprehensive validation script for all PDF outputs against their references
"""
import json
from pathlib import Path
from typing import Dict, List, Any

def validate_json_output(current_file: str, reference_file: str, form_name: str) -> dict:
    """Validate a JSON output against its reference"""
    current_path = Path(current_file)
    reference_path = Path(f"references/Matching JSON References/{reference_file}")
    
    result = {
        'form_name': form_name,
        'current_file': current_file,
        'reference_file': reference_file,
        'validation_passed': False,
        'issues': []
    }
    
    if not current_path.exists():
        result['issues'].append(f"❌ Current file not found: {current_file}")
        return result
        
    if not reference_path.exists():
        result['issues'].append(f"❌ Reference file not found: {reference_path}")
        return result
    
    try:
        with open(current_path, 'r') as f:
            current = json.load(f)
        with open(reference_path, 'r') as f:
            reference = json.load(f)
    except json.JSONDecodeError as e:
        result['issues'].append(f"❌ JSON decode error: {e}")
        return result
    
    # Get keys
    ref_keys = [item['key'] for item in reference]
    cur_keys = [item['key'] for item in current]
    
    # Check missing and extra keys
    missing = [k for k in ref_keys if k not in cur_keys]
    extra = [k for k in cur_keys if k not in ref_keys]
    matching = [k for k in ref_keys if k in cur_keys]
    
    result['ref_count'] = len(reference)
    result['cur_count'] = len(current)
    result['matching'] = len(matching)
    result['missing'] = missing
    result['extra'] = extra
    result['accuracy'] = len(matching) / len(reference) * 100 if reference else 0
    
    # Add specific issues
    if missing:
        result['issues'].append(f"❌ Missing {len(missing)} fields: {missing}")
    if extra:
        result['issues'].append(f"⚠️  {len(extra)} extra fields: {extra}")
    
    # Check field order for first 5 fields
    order_issues = []
    for i in range(min(5, len(current), len(reference))):
        if current[i]['key'] != reference[i]['key']:
            order_issues.append(f"Position {i+1}: current='{current[i]['key']}' vs ref='{reference[i]['key']}'")
    
    if order_issues:
        result['issues'].append(f"❌ Field order issues: {order_issues}")
    
    # Detailed field comparison for matching keys
    field_issues = []
    for key in matching[:3]:  # Check first 3 matching fields
        ref_field = next(item for item in reference if item['key'] == key)
        cur_field = next(item for item in current if item['key'] == key)
        
        if ref_field.get('type') != cur_field.get('type'):
            field_issues.append(f"{key}: type mismatch")
        if ref_field.get('section') != cur_field.get('section'):
            field_issues.append(f"{key}: section mismatch")
    
    if field_issues:
        result['issues'].append(f"⚠️  Field details: {field_issues}")
    
    # Overall validation
    if not missing and not extra and len(order_issues) == 0:
        result['validation_passed'] = True
        result['issues'] = ["✅ Perfect match!"]
    
    return result

def main():
    """Validate all forms"""
    forms_to_validate = [
        ('npf.json', 'npf.json', 'NPF Patient Form'),
        ('consent_crown_bridge_prosthetics.json', 'consent_crown_bridge_prosthetics.json', 'Crown Bridge Consent'),
        ('tooth20removal20consent20form.json', 'tooth20removal20consent20form.json', 'Tooth Removal Consent'),
    ]
    
    print("📊 Comprehensive Form Validation Report")
    print("=" * 60)
    
    results = []
    for current_file, reference_file, form_name in forms_to_validate:
        result = validate_json_output(current_file, reference_file, form_name)
        results.append(result)
        
        print(f"\n🔍 {form_name}")
        print(f"   Current: {result['cur_count']} fields | Reference: {result['ref_count']} fields")
        print(f"   Accuracy: {result['accuracy']:.1f}% ({result['matching']}/{result['ref_count']} matching)")
        
        for issue in result['issues']:
            print(f"   {issue}")
    
    # Summary
    print(f"\n📈 Summary:")
    passed = sum(1 for r in results if r['validation_passed'])
    print(f"   ✅ Passed: {passed}/{len(results)} forms")
    print(f"   ❌ Failed: {len(results) - passed}/{len(results)} forms")
    
    if passed == len(results):
        print(f"\n🎉 ALL VALIDATIONS PASSED!")
    else:
        print(f"\n⚠️  ISSUES FOUND - See details above")
    
    return results

if __name__ == "__main__":
    main()