#!/usr/bin/env python3

import json

# Load test output
with open('test_fix2_output.json', 'r') as f:
    current = json.load(f)

print("=== ANALYZING WORK ADDRESS FIELDS ===")

# Check the specific fields that are jumping sections
work_fields = ['street_3', 'city_2_2', 'state_2_2', 'zip_2_2']

print("Work address fields analysis:")
for i, field in enumerate(current):
    if field['key'] in work_fields:
        print(f"  {i+1:2d}. {field['key']:15s} | Section: {field.get('section'):25s} | Title: {field['title']}")

# Check what's around position 49 more broadly
print("\nFields from position 45-55:")
for i in range(44, min(55, len(current))):
    field = current[i]
    section_marker = " <-- SECTION JUMP" if i == 48 else ""  # Position 49 is index 48
    print(f"  {i+1:2d}. {field['key']:30s} | {field.get('section', 'Unknown'):25s}{section_marker}")