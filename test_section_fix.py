#!/usr/bin/env python3

import json

# Load test output
with open('test_fix3_output.json', 'r') as f:
    current = json.load(f)

print("=== TESTING SECTION BOUNDARY FIX #3 ===")

# Check if there's still section boundary jumping
print("\nSection boundaries:")
current_section = ""
section_breaks = []
for i, field in enumerate(current):
    if field.get('section') != current_section:
        current_section = field.get('section')
        section_breaks.append((i+1, current_section))
        print(f"  Position {i+1}: Section '{current_section}' starts")

# Find the problem fields
problem_fields = {}
for i, field in enumerate(current):
    if field['key'] == 'relationship_to_patient_2':
        problem_fields['relationship_to_patient_2'] = i+1
    if field['key'] == 'insurance_company_2':
        problem_fields['insurance_company_2'] = i+1
    if field['key'] == 'phone_2':
        problem_fields['phone_2'] = i+1

print("\nProblem field positions after fix:")
for key, pos in problem_fields.items():
    print(f"  {key}: position {pos}")

# Check if the section jumping is fixed
children_section_start = None
children_section_end = None
for pos, section in section_breaks:
    if section == "FOR CHILDREN/MINORS ONLY":
        children_section_start = pos
    elif children_section_start and section != "FOR CHILDREN/MINORS ONLY":
        children_section_end = pos - 1
        break

print(f"\nChildren section spans: positions {children_section_start} to {children_section_end}")

# Check for section jumping within children section
has_section_jump = False
for i, field in enumerate(current):
    if (children_section_start and children_section_end and
        children_section_start <= i+1 <= children_section_end and
        field.get('section') != "FOR CHILDREN/MINORS ONLY"):
        print(f"❌ Section jump detected at position {i+1}: {field['key']} in section '{field.get('section')}'")
        has_section_jump = True

if not has_section_jump and children_section_start:
    print("✅ No section jumping detected within children section")

print("\n=== IMPROVEMENT CHECK ===")
original_pos = 47  # relationship_to_patient_2 original position
new_pos = problem_fields.get('relationship_to_patient_2', original_pos)
if new_pos < original_pos:
    print(f"✅ relationship_to_patient_2 moved from {original_pos} to {new_pos} (improvement: -{original_pos - new_pos})")
elif new_pos == original_pos:
    print(f"⚠️  relationship_to_patient_2 still at position {new_pos} (no change)")
else:
    print(f"❌ relationship_to_patient_2 moved from {original_pos} to {new_pos} (worse: +{new_pos - original_pos})")