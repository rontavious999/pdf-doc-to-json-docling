#!/usr/bin/env python3
"""
Example demonstrating custom placeholders in consent forms

This example shows how the consent converter handles:
1. Custom placeholders (planned_procedure, diagnosis, alternative_treatment)
2. Witness and doctor signature exclusion
3. Provider placeholders
"""

from pathlib import Path
from consent_converter import ConsentToJSONConverter
import json


def example_custom_placeholders():
    """Example showing custom placeholder replacement"""
    print("Example: Custom Placeholders in Consent Forms")
    print("=" * 70)
    
    converter = ConsentToJSONConverter()
    
    # Test with a real consent document
    input_file = Path("docx/Informed Consent for Biopsy.docx")
    
    if input_file.exists():
        result = converter.convert_consent_to_json(input_file, output_path=None)
        spec = result['spec']
        
        # Find the consent text field
        form_field = next((f for f in spec if f['key'] == 'form_1'), None)
        if form_field:
            html_text = form_field['control'].get('html_text', '')
            
            # Check for various placeholders
            placeholders = {
                '{{provider}}': 'Provider/Doctor name',
                '{{planned_procedure}}': 'Planned procedure description',
                '{{diagnosis}}': 'Patient diagnosis',
                '{{alternative_treatment}}': 'Alternative treatment options',
                '{{patient_name}}': 'Patient name',
                '{{patient_dob}}': 'Patient date of birth',
                '{{tooth_or_site}}': 'Tooth number or site'
            }
            
            print("\nPlaceholders detected in consent form:")
            print("-" * 70)
            
            found_count = 0
            for placeholder, description in placeholders.items():
                count = html_text.count(placeholder)
                if count > 0:
                    print(f"✓ {placeholder:30} - {description} ({count}x)")
                    found_count += 1
            
            if found_count == 0:
                print("ℹ No custom placeholders needed for this consent")
            
            print(f"\nTotal unique placeholders: {found_count}")
            
        # Check for excluded fields
        field_keys = [f['key'] for f in spec]
        print("\n" + "-" * 70)
        print("Witness and Doctor Signature Exclusion:")
        print("-" * 70)
        
        has_witness = any('witness' in key.lower() for key in field_keys)
        has_doctor_sig = any('doctor' in key.lower() and 'signature' in key.lower() 
                            for key in field_keys)
        
        if not has_witness:
            print("✓ No witness fields in output (correctly excluded)")
        else:
            print("✗ Warning: Witness fields detected")
        
        if not has_doctor_sig:
            print("✓ No doctor signature fields in output (correctly excluded)")
        else:
            print("✗ Warning: Doctor signature fields detected")
        
        # Show extracted fields
        print("\n" + "-" * 70)
        print("Extracted Fields:")
        print("-" * 70)
        for field in spec:
            print(f"  • {field['type']:12} - {field['key']:30} ({field['section']})")
        
        print("\n" + "-" * 70)
        print(f"Summary: {result['field_count']} fields in {result['section_count']} sections")
        print(f"Validation: {'PASSED ✓' if result['is_valid'] else 'FAILED ✗'}")
    else:
        print(f"✗ File not found: {input_file}")


def example_demonstrate_all_placeholders():
    """Example showing all supported placeholders"""
    print("\n\nSupported Custom Placeholders")
    print("=" * 70)
    
    placeholders = [
        {
            'name': '{{provider}}',
            'description': 'Provider/doctor name',
            'patterns': [
                'Dr. _____',
                'authorize Dr. _____',
                'consent to Dr. _____'
            ]
        },
        {
            'name': '{{planned_procedure}}',
            'description': 'Planned medical/dental procedure',
            'patterns': [
                'Planned Procedure: _____',
                'Planned procedure: _____'
            ]
        },
        {
            'name': '{{diagnosis}}',
            'description': 'Patient diagnosis',
            'patterns': [
                'Diagnosis: _____',
                'diagnosis: _____'
            ]
        },
        {
            'name': '{{alternative_treatment}}',
            'description': 'Alternative treatment options',
            'patterns': [
                'Alternative Treatment: _____',
                'alternative treatment: _____'
            ]
        },
        {
            'name': '{{patient_name}}',
            'description': 'Patient name',
            'patterns': [
                'Patient Name: _____',
                'I, _____ (print name)'
            ]
        },
        {
            'name': '{{patient_dob}}',
            'description': 'Patient date of birth',
            'patterns': [
                'DOB: _____',
                'Date of Birth: _____'
            ]
        },
        {
            'name': '{{tooth_or_site}}',
            'description': 'Tooth number or procedure site',
            'patterns': [
                'Tooth No(s). _____',
                'Tooth Number: _____'
            ]
        }
    ]
    
    for i, placeholder in enumerate(placeholders, 1):
        print(f"\n{i}. {placeholder['name']}")
        print(f"   Description: {placeholder['description']}")
        print(f"   Matches patterns like:")
        for pattern in placeholder['patterns']:
            print(f"     - {pattern}")
    
    print("\n" + "=" * 70)
    print("Note: All patterns are case-insensitive and support various")
    print("      underscore lengths (e.g., ___, _____, _____________)")


def example_exclusion_rules():
    """Example showing what gets excluded"""
    print("\n\nExclusion Rules")
    print("=" * 70)
    
    print("\nThe following are automatically excluded from consent forms:")
    print("\n1. Witness Fields:")
    print("   • Witness Signature")
    print("   • Witness Name / Printed Name")
    print("   • Witness Date")
    print("   • Witness Relationship")
    print("   • Witnessed by")
    
    print("\n2. Doctor/Provider Signature Fields:")
    print("   • Doctor Signature")
    print("   • Dentist Signature")
    print("   • Physician Signature")
    print("   • Dr. Signature")
    print("   • Practitioner Signature")
    print("   • Provider Signature")
    print("   • Clinician Signature")
    
    print("\n3. Other Excluded:")
    print("   • Legally authorized representative (in witness context)")
    
    print("\nNote: Patient signatures and information are preserved")
    print("      Only witness and provider signature fields are excluded")


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("Consent Converter - Custom Placeholder Examples")
    print("=" * 70)
    
    example_custom_placeholders()
    example_demonstrate_all_placeholders()
    example_exclusion_rules()
    
    print("\n" + "=" * 70)
    print("For more examples, see CONSENT_CONVERTER_README.md")
    print("=" * 70 + "\n")
