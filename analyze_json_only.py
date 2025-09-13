#!/usr/bin/env python3

import json

# Load current output
with open('current_npf_output.json', 'r') as f:
    current = json.load(f)

print("=== DEBUGGING FIELD ORDER ISSUES ===")

# Find the problem fields
problem_fields = {}
for i, field in enumerate(current):
    if field['key'] == 'relationship_to_patient_2':
        problem_fields['relationship_to_patient_2'] = i+1
    if field['key'] == 'insurance_company_2':
        problem_fields['insurance_company_2'] = i+1
    if field['key'] == 'phone_2':
        problem_fields['phone_2'] = i+1

print("Problem field positions in current output:")
for key, pos in problem_fields.items():
    print(f"  {key}: position {pos}")

print("\nFields around relationship_to_patient_2 (position 47):")
for i in range(40, min(55, len(current))):
    field = current[i]
    print(f"  {i+1:2d}. {field['key']:30s} | {field.get('section', 'Unknown'):25s}")

print("\nSecondary Dental Plan section fields:")
for i, field in enumerate(current):
    if field.get('section') == 'Secondary Dental Plan':
        print(f"  {i+1:2d}. {field['key']:30s} | {field['title']}")

# Check if there's a pattern in section boundaries
print("\nSection boundaries:")
current_section = ""
for i, field in enumerate(current):
    if field.get('section') != current_section:
        current_section = field.get('section')
        print(f"  Position {i+1}: Section '{current_section}' starts")