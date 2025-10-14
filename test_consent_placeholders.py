#!/usr/bin/env python3
"""
Test custom placeholders in consent_converter.py

This test validates that:
1. Planned Procedure placeholders are correctly replaced
2. Diagnosis placeholders are correctly replaced
3. Alternative Treatment placeholders are correctly replaced
4. Witness and doctor signature fields are properly excluded
"""

import sys
import re
from pathlib import Path

# Add the parent directory to the path for imports
sys.path.insert(0, str(Path(__file__).parent))

from consent_converter import ConsentFormFieldExtractor


def test_placeholder_replacement():
    """Test that custom placeholders are correctly replaced in consent HTML"""
    print("Testing custom placeholder replacement...")
    
    extractor = ConsentFormFieldExtractor()
    
    # Test data with various placeholder patterns
    test_cases = [
        # Planned Procedure patterns
        {
            'input': 'Planned Procedure: _____',
            'expected': 'Planned Procedure: {{planned_procedure}}',
            'placeholder': 'planned_procedure'
        },
        {
            'input': 'Planned Procedure: _______________',
            'expected': 'Planned Procedure: {{planned_procedure}}',
            'placeholder': 'planned_procedure'
        },
        {
            'input': 'Planned procedure: _______',
            'expected': '{{planned_procedure}}',  # Just check for placeholder, not exact case
            'placeholder': 'planned_procedure'
        },
        # Diagnosis patterns
        {
            'input': 'Diagnosis: _____',
            'expected': 'Diagnosis: {{diagnosis}}',
            'placeholder': 'diagnosis'
        },
        {
            'input': 'Diagnosis: _______________',
            'expected': 'Diagnosis: {{diagnosis}}',
            'placeholder': 'diagnosis'
        },
        {
            'input': 'diagnosis: _______',
            'expected': '{{diagnosis}}',  # Just check for placeholder, not exact case
            'placeholder': 'diagnosis'
        },
        # Alternative Treatment patterns
        {
            'input': 'Alternative Treatment: _____',
            'expected': 'Alternative Treatment: {{alternative_treatment}}',
            'placeholder': 'alternative_treatment'
        },
        {
            'input': 'Alternative Treatment: _______________',
            'expected': 'Alternative Treatment: {{alternative_treatment}}',
            'placeholder': 'alternative_treatment'
        },
        {
            'input': 'alternative treatment: _______',
            'expected': '{{alternative_treatment}}',  # Just check for placeholder, not exact case
            'placeholder': 'alternative_treatment'
        },
    ]
    
    # Create consent HTML with test data
    for i, test_case in enumerate(test_cases):
        consent_lines = [test_case['input']]
        html_content, _ = extractor._create_enhanced_consent_html(
            consent_lines, 
            test_case['input'], 
            []  # No provider patterns for this test
        )
        
        # Check if the placeholder was replaced
        if test_case['expected'] in html_content:
            print(f"✓ Test {i+1} passed: {test_case['placeholder']} placeholder replaced correctly")
        else:
            print(f"✗ Test {i+1} failed: {test_case['placeholder']} placeholder NOT replaced")
            print(f"  Input: {test_case['input']}")
            print(f"  Expected: {test_case['expected']}")
            print(f"  Got: {html_content}")
            return False
    
    print("All placeholder replacement tests passed!\n")
    return True


def test_witness_and_doctor_signature_exclusion():
    """Test that witness and doctor signature fields are properly excluded"""
    print("Testing witness and doctor signature exclusion...")
    
    extractor = ConsentFormFieldExtractor()
    
    # Test data with various witness and doctor signature patterns
    test_cases = [
        # Witness signatures
        {'input': 'Witness Signature:', 'should_exclude': True},
        {'input': 'Witness Name:', 'should_exclude': True},
        {'input': 'Witness Printed Name:', 'should_exclude': True},
        {'input': 'Witness Date:', 'should_exclude': True},
        {'input': 'Witnessed by:', 'should_exclude': True},
        {'input': 'Witness:', 'should_exclude': True},
        {'input': 'Witness Relationship:', 'should_exclude': True},
        
        # Doctor signatures
        {'input': 'Doctor Signature:', 'should_exclude': True},
        {'input': 'Dentist Signature:', 'should_exclude': True},
        {'input': 'Physician Signature:', 'should_exclude': True},
        {'input': 'Dr. Signature:', 'should_exclude': True},
        {'input': 'Practitioner Signature:', 'should_exclude': True},
        {'input': 'Provider Signature:', 'should_exclude': True},
        {'input': 'Clinician Signature:', 'should_exclude': True},
        
        # Should NOT exclude (patient fields)
        {'input': 'Patient Name:', 'should_exclude': False},
        {'input': 'Patient Signature:', 'should_exclude': False},
        {'input': 'Signature:', 'should_exclude': False},
        {'input': 'Date Signed:', 'should_exclude': False},
        {'input': 'Printed Name:', 'should_exclude': False},
    ]
    
    for i, test_case in enumerate(test_cases):
        result = extractor._is_witness_or_doctor_signature_field(test_case['input'].lower())
        expected = test_case['should_exclude']
        
        if result == expected:
            status = "excluded" if result else "kept"
            print(f"✓ Test {i+1} passed: '{test_case['input']}' correctly {status}")
        else:
            print(f"✗ Test {i+1} failed: '{test_case['input']}'")
            print(f"  Expected to be {'excluded' if expected else 'kept'}, but was {'excluded' if result else 'kept'}")
            return False
    
    print("All witness and doctor signature exclusion tests passed!\n")
    return True


def test_content_filtering():
    """Test that witness/doctor signatures are removed from HTML content"""
    print("Testing content filtering for witness/doctor signatures...")
    
    extractor = ConsentFormFieldExtractor()
    
    # Test content with witness and doctor signature lines
    test_content = """Patient Name: {{patient_name}}<br>Witness Signature: ___<br>Doctor Signature: ___<br>Date Signed: ___"""
    
    filtered_content = extractor._remove_witness_and_doctor_signatures(test_content)
    
    # Check that witness and doctor signatures were removed
    if 'Witness Signature' in filtered_content:
        print("✗ Failed: Witness Signature was not removed")
        print(f"  Content: {filtered_content}")
        return False
    
    if 'Doctor Signature' in filtered_content:
        print("✗ Failed: Doctor Signature was not removed")
        print(f"  Content: {filtered_content}")
        return False
    
    # Check that patient name and date signed were kept
    if 'Patient Name' not in filtered_content:
        print("✗ Failed: Patient Name was incorrectly removed")
        print(f"  Content: {filtered_content}")
        return False
    
    if 'Date Signed' not in filtered_content:
        print("✗ Failed: Date Signed was incorrectly removed")
        print(f"  Content: {filtered_content}")
        return False
    
    print("✓ Content filtering test passed")
    print("Content filtering tests passed!\n")
    return True


def test_avoid_double_replacement():
    """Test that placeholders are not replaced twice"""
    print("Testing that placeholders avoid double replacement...")
    
    extractor = ConsentFormFieldExtractor()
    
    # Test with already replaced placeholder
    test_cases = [
        {
            'input': 'Planned Procedure: {{planned_procedure}}',
            'expected_count': 1  # Should have exactly one placeholder, not two
        },
        {
            'input': 'Diagnosis: {{diagnosis}}',
            'expected_count': 1
        },
        {
            'input': 'Alternative Treatment: {{alternative_treatment}}',
            'expected_count': 1
        },
    ]
    
    for i, test_case in enumerate(test_cases):
        consent_lines = [test_case['input']]
        html_content, _ = extractor._create_enhanced_consent_html(
            consent_lines,
            test_case['input'],
            []
        )
        
        # Count occurrences of the placeholder pattern
        placeholder_pattern = r'\{\{[^}]+\}\}'
        matches = re.findall(placeholder_pattern, html_content)
        
        if len(matches) == test_case['expected_count']:
            print(f"✓ Test {i+1} passed: No double replacement")
        else:
            print(f"✗ Test {i+1} failed: Expected {test_case['expected_count']} placeholder(s), found {len(matches)}")
            print(f"  Content: {html_content}")
            return False
    
    print("All double replacement prevention tests passed!\n")
    return True


def main():
    """Run all tests"""
    print("Running consent placeholder tests...\n")
    print("=" * 70)
    print()
    
    all_passed = True
    
    try:
        if not test_placeholder_replacement():
            all_passed = False
        
        if not test_witness_and_doctor_signature_exclusion():
            all_passed = False
        
        if not test_content_filtering():
            all_passed = False
        
        if not test_avoid_double_replacement():
            all_passed = False
        
        print("=" * 70)
        if all_passed:
            print("🎉 All tests passed!")
            print("\nSummary:")
            print("- Custom placeholders (planned_procedure, diagnosis, alternative_treatment) work correctly")
            print("- Witness and doctor signature fields are properly excluded")
            print("- Content filtering removes witness/doctor signatures from HTML")
            print("- Double replacement is prevented")
        else:
            print("❌ Some tests failed")
            sys.exit(1)
        
    except Exception as e:
        print(f"❌ Test error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
