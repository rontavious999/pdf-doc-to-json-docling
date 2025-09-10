#!/usr/bin/env python3
"""
Validation script to compare generated JSON with reference JSON files
"""

import json
import argparse
from pathlib import Path
from typing import Dict, List, Any, Set


def load_json(file_path: Path) -> List[Dict[str, Any]]:
    """Load JSON file"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def extract_field_keys(spec: List[Dict[str, Any]]) -> Set[str]:
    """Extract all field keys from a spec"""
    keys = set()
    
    def collect_keys(items):
        for item in items:
            if 'key' in item:
                keys.add(item['key'])
            if item.get('type') == 'multiradio' and 'control' in item:
                nested = item['control'].get('questions', [])
                collect_keys(nested)
    
    collect_keys(spec)
    return keys


def compare_specs(generated: List[Dict[str, Any]], reference: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compare generated spec with reference spec"""
    gen_keys = extract_field_keys(generated)
    ref_keys = extract_field_keys(reference)
    
    comparison = {
        "generated_count": len(generated),
        "reference_count": len(reference),
        "generated_keys": len(gen_keys),
        "reference_keys": len(ref_keys),
        "matching_keys": len(gen_keys & ref_keys),
        "missing_keys": list(ref_keys - gen_keys),
        "extra_keys": list(gen_keys - ref_keys),
        "coverage_percentage": (len(gen_keys & ref_keys) / len(ref_keys)) * 100 if ref_keys else 0
    }
    
    return comparison


def validate_against_references(generated_dir: Path, reference_dir: Path):
    """Validate generated JSONs against reference JSONs"""
    results = []
    
    # Find matching pairs
    for gen_file in generated_dir.glob("*.json"):
        if gen_file.name == "conversion_summary.json":
            continue
            
        # Look for corresponding reference file
        ref_file = reference_dir / f"{gen_file.stem}.json"
        
        if not ref_file.exists():
            print(f"Warning: No reference file found for {gen_file.name}")
            continue
        
        print(f"\nValidating {gen_file.name}...")
        
        try:
            generated = load_json(gen_file)
            reference = load_json(ref_file)
            
            comparison = compare_specs(generated, reference)
            
            print(f"  Generated: {comparison['generated_count']} fields ({comparison['generated_keys']} unique keys)")
            print(f"  Reference: {comparison['reference_count']} fields ({comparison['reference_keys']} unique keys)")
            print(f"  Coverage: {comparison['coverage_percentage']:.1f}% ({comparison['matching_keys']}/{comparison['reference_keys']} keys)")
            
            if comparison['missing_keys']:
                print(f"  Missing keys ({len(comparison['missing_keys'])}): {comparison['missing_keys'][:5]}{'...' if len(comparison['missing_keys']) > 5 else ''}")
            
            if comparison['extra_keys']:
                print(f"  Extra keys ({len(comparison['extra_keys'])}): {comparison['extra_keys'][:5]}{'...' if len(comparison['extra_keys']) > 5 else ''}")
            
            results.append({
                "file": gen_file.name,
                "comparison": comparison
            })
            
        except Exception as e:
            print(f"  Error: {e}")
            results.append({
                "file": gen_file.name,
                "error": str(e)
            })
    
    # Summary
    if results:
        print(f"\n{'='*50}")
        print("SUMMARY")
        print(f"{'='*50}")
        
        valid_results = [r for r in results if 'comparison' in r]
        if valid_results:
            avg_coverage = sum(r['comparison']['coverage_percentage'] for r in valid_results) / len(valid_results)
            print(f"Average coverage: {avg_coverage:.1f}%")
            
            best = max(valid_results, key=lambda r: r['comparison']['coverage_percentage'])
            worst = min(valid_results, key=lambda r: r['comparison']['coverage_percentage'])
            
            print(f"Best coverage: {best['file']} ({best['comparison']['coverage_percentage']:.1f}%)")
            print(f"Worst coverage: {worst['file']} ({worst['comparison']['coverage_percentage']:.1f}%)")
    
    return results


def main():
    parser = argparse.ArgumentParser(description="Validate generated JSON against reference files")
    parser.add_argument("generated_dir", help="Directory with generated JSON files")
    parser.add_argument("reference_dir", help="Directory with reference JSON files")
    
    args = parser.parse_args()
    
    generated_dir = Path(args.generated_dir)
    reference_dir = Path(args.reference_dir)
    
    if not generated_dir.exists():
        print(f"Error: Generated directory not found: {generated_dir}")
        return 1
    
    if not reference_dir.exists():
        print(f"Error: Reference directory not found: {reference_dir}")
        return 1
    
    validate_against_references(generated_dir, reference_dir)
    return 0


if __name__ == "__main__":
    exit(main())