#!/usr/bin/env python3

import json

def main():
    # Load current output and reference
    with open("improved_test_output.json") as f:
        current = json.load(f)
    
    with open("references/Matching JSON References/npf.json") as f:
        reference = json.load(f)
    
    print(f"Current: {len(current)} fields")
    print(f"Reference: {len(reference)} fields")
    print(f"Difference: +{len(current) - len(reference)} fields\n")
    
    # Get keys from both
    current_keys = [field["key"] for field in current]
    reference_keys = [field["key"] for field in reference]
    
    current_keys_set = set(current_keys)
    reference_keys_set = set(reference_keys)
    
    # Find extra keys
    extra_keys = current_keys_set - reference_keys_set
    print(f"Extra keys in current ({len(extra_keys)}):")
    for key in sorted(extra_keys):
        field = next(f for f in current if f["key"] == key)
        print(f"  {key:30} | {field.get('title', '')[:40]:40} | {field.get('section', '')}")
    
    # Find missing keys
    missing_keys = reference_keys_set - current_keys_set
    print(f"\nMissing keys from reference ({len(missing_keys)}):")
    for key in sorted(missing_keys):
        field = next(f for f in reference if f["key"] == key)
        print(f"  {key:30} | {field.get('title', '')[:40]:40} | {field.get('section', '')}")
    
    # Check for duplicates in current
    from collections import Counter
    key_counts = Counter(current_keys)
    duplicates = {k: v for k, v in key_counts.items() if v > 1}
    if duplicates:
        print(f"\nDuplicate keys in current ({len(duplicates)}):")
        for key, count in duplicates.items():
            print(f"  {key}: {count} times")

if __name__ == "__main__":
    main()