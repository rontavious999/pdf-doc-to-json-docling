#!/usr/bin/env python3
"""Temporary debug version to trace parse_inline_fields logic"""

import re

def debug_parse_inline_fields(line: str, context_lines=None):
    """Debug version of parse_inline_fields to trace logic"""
    fields = []
    seen_fields = set()
    
    print(f"=== DEBUG parse_inline_fields ===")
    print(f"Line: {line}")
    print(f"Context: {context_lines}")
    
    # Get context for determining if we should allow duplicate field names
    if context_lines:
        context_text = ' '.join(context_lines).lower()
        is_work_address = 'work address' in context_text
        is_different_from_patient = 'if different from patient' in context_text
        is_different_from_above = 'if different from above' in context_text
        allow_duplicates = is_work_address or is_different_from_patient or is_different_from_above
        print(f"Work address: {is_work_address}, Different from patient: {is_different_from_patient}")
        print(f"Different from above: {is_different_from_above}, Allow duplicates: {allow_duplicates}")
    else:
        allow_duplicates = False
        print(f"No context, allow_duplicates: {allow_duplicates}")

    # Test the regex pattern
    pattern = r'([A-Za-z][A-Za-z\s\#\/\(\)\-\.]{1,35}?)(?:_{4,}|:\s*_{2,})'
    matches = re.finditer(pattern, line)
    
    for match in matches:
        field_name = match.group(1).strip()
        print(f"\\nProcessing field: '{field_name}'")
        print(f"  Seen fields so far: {seen_fields}")
        print(f"  Field in seen_fields: {field_name in seen_fields}")
        
        # Test the conditions
        len_ok = len(field_name) >= 2 and len(field_name) <= 35
        not_excluded = field_name.lower() not in [
            'and', 'or', 'the', 'of', 'to', 'for', 'in', 'with', 'if', 'is', 'are', 
            'patient name', 'please', 'check', 'all', 'that', 'apply', 'form',
            'information', 'section', 'date', 'time', 'page'
        ]
        not_seen = field_name not in seen_fields
        not_uppercase = not field_name.isupper() or field_name.lower() in ['mi', 'ssn', 'id', 'dl', 'dob']
        not_repeated = not re.match(r'^(.)\1+$', field_name.replace(' ', ''))
        has_letters = re.search(r'[A-Za-z]', field_name)
        
        normal_condition = len_ok and not_excluded and not_seen and not_uppercase and not_repeated and has_letters
        
        # Special duplicate condition
        is_address_field = field_name.lower() in ['street', 'city', 'state', 'zip']
        duplicate_condition = allow_duplicates and is_address_field and len_ok and has_letters
        
        print(f"  Length OK (2-35): {len_ok}")
        print(f"  Not excluded word: {not_excluded}")
        print(f"  Not seen: {not_seen}")
        print(f"  Not uppercase (or allowed): {not_uppercase}")
        print(f"  Not repeated chars: {not_repeated}")
        print(f"  Has letters: {has_letters}")
        print(f"  Normal condition: {normal_condition}")
        print(f"  Is address field: {is_address_field}")
        print(f"  Duplicate condition: {duplicate_condition}")
        print(f"  Final condition: {normal_condition or duplicate_condition}")
        
        if normal_condition or duplicate_condition:
            print(f"  ✓ Adding field: {field_name}")
            fields.append((field_name, line))
            seen_fields.add(field_name)
        else:
            print(f"  ✗ Filtering out field: {field_name}")
    
    print(f"\\nFinal result: {[f[0] for f in fields]}")
    return fields

# Test with the work address line
line = 'Street__________________________ City_____________________ State_____ Zip_________'
context_lines = ['', 'Work Address:', '', line, '']
debug_parse_inline_fields(line, context_lines)