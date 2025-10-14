#!/usr/bin/env python3
"""
Test fixes for Labial Frenectomy consent form issues
 
This test validates the three key fixes:
1. Section title is "Labial Frenectomy Informed Consent" (not generic "Form")
2. Patient's Name: placeholder is replaced with {{patient_name}}
3. Parent/Guardian's Name is extracted as a separate input field
"""

import sys
import re
from pathlib import Path

# Add the parent directory to the path for imports
sys.path.insert(0, str(Path(__file__).parent))

from consent_converter import ConsentFormFieldExtractor


def test_title_ending_with_informed_consent():
    """Test that titles ending with 'Informed Consent' are detected"""
    print("Testing title detection for 'X Informed Consent' pattern...")
    
    extractor = ConsentFormFieldExtractor()
    
    # Test case: "Labial Frenectomy Informed Consent"
    test_lines = [
        'Labial Frenectomy Informed Consent',
        'Patient\'s Name: \t\t\t\t\t\t\tPatient Date of Birth:',
        'This is the consent text content.'
    ]
    
    consent_html, detected_title = extractor._create_enhanced_consent_html(
        test_lines, '\n'.join(test_lines), []
    )
    
    assert detected_title == 'Labial Frenectomy Informed Consent', \
        f"Expected title 'Labial Frenectomy Informed Consent', got '{detected_title}'"
    
    # Verify title is in HTML but not duplicated in content
    assert 'Labial Frenectomy Informed Consent' in consent_html
    # Title should appear in <strong> tag once
    assert consent_html.count('<strong>Labial Frenectomy Informed Consent</strong>') == 1
    
    print("✓ Title detection working correctly")
    return True


def test_patients_name_with_apostrophe():
    """Test that Patient's Name (with apostrophe) gets placeholder"""
    print("Testing Patient's Name placeholder replacement...")
    
    extractor = ConsentFormFieldExtractor()
    
    # Test various patterns
    test_cases = [
        {
            'input': 'Patient\'s Name: \t\t\t\t\t\t\tPatient Date of Birth:',
            'expected_placeholder': '{{patient_name}}'
        },
        {
            'input': "Patient's Name: __________",
            'expected_placeholder': '{{patient_name}}'
        },
        {
            'input': "PATIENT'S NAME: ",
            'expected_placeholder': '{{patient_name}}'
        }
    ]
    
    for test_case in test_cases:
        test_lines = ['Title', test_case['input'], 'Content']
        consent_html, _ = extractor._create_enhanced_consent_html(
            test_lines, '\n'.join(test_lines), []
        )
        
        assert test_case['expected_placeholder'] in consent_html, \
            f"Expected '{test_case['expected_placeholder']}' in output for input '{test_case['input']}'"
        
        # Verify the apostrophe form is preserved
        assert "Patient's Name:" in consent_html or "Patient\\'s Name:" in consent_html
    
    print("✓ Patient's Name placeholder working correctly")
    return True


def test_parent_guardian_name_field_extraction():
    """Test that Parent/Guardian's Name is extracted as a separate field"""
    print("Testing Parent/Guardian's Name field extraction...")
    
    extractor = ConsentFormFieldExtractor()
    
    # Simulate text lines from Labial Frenectomy document
    text_lines = [
        'Labial Frenectomy Informed Consent',
        'Patient\'s Name: \t\t\t\t\t\t\tPatient Date of Birth:',
        'The recommendation for a lip (labial) frenectomy has been made.',
        'I understand the above statements and have had my questions answered',
        'Parent/Guardian\'s Name: __________________________________',
        'Parent/Guardian\'s Signature: ________________________________',
        'Date: __________________'
    ]
    
    # Extract fields
    fields = extractor.extract_consent_form_fields(text_lines)
    
    # Check that parent_guardian_name field exists
    parent_guardian_field = next((f for f in fields if f.key == 'parent_guardian_name'), None)
    
    assert parent_guardian_field is not None, \
        "Parent/Guardian Name field not found in extracted fields"
    
    assert parent_guardian_field.title == 'Parent/Guardian Name', \
        f"Expected title 'Parent/Guardian Name', got '{parent_guardian_field.title}'"
    
    assert parent_guardian_field.field_type == 'input', \
        f"Expected field_type 'input', got '{parent_guardian_field.field_type}'"
    
    assert parent_guardian_field.control.get('input_type') == 'name', \
        f"Expected input_type 'name', got '{parent_guardian_field.control.get('input_type')}'"
    
    assert parent_guardian_field.section == 'Signature', \
        f"Expected section 'Signature', got '{parent_guardian_field.section}'"
    
    print("✓ Parent/Guardian Name field extraction working correctly")
    return True


def test_parent_guardian_name_not_in_html():
    """Test that Parent/Guardian's Name is NOT in the HTML content"""
    print("Testing Parent/Guardian's Name is filtered from HTML...")
    
    extractor = ConsentFormFieldExtractor()
    
    # Simulate text lines
    text_lines = [
        'Labial Frenectomy Informed Consent',
        'Patient\'s Name: \t\t\t\t\t\t\tPatient Date of Birth:',
        'The recommendation for a lip (labial) frenectomy has been made.',
        'I understand the above statements',
        'Parent/Guardian\'s Name: __________________________________'
    ]
    
    # Extract fields
    fields = extractor.extract_consent_form_fields(text_lines)
    
    # Get the HTML content field
    html_field = next((f for f in fields if f.field_type == 'text'), None)
    assert html_field is not None, "HTML content field not found"
    
    html_content = html_field.control.get('html_text', '')
    
    # Verify Parent/Guardian's Name is NOT in the HTML
    assert 'Parent/Guardian' not in html_content, \
        "Parent/Guardian's Name should not appear in HTML content - it should be a separate field"
    
    print("✓ Parent/Guardian Name correctly filtered from HTML")
    return True


def test_parent_guardian_signature_still_filtered():
    """Test that Parent/Guardian's Signature is still filtered (not extracted)"""
    print("Testing Parent/Guardian's Signature is still filtered...")
    
    extractor = ConsentFormFieldExtractor()
    
    # Simulate text lines
    text_lines = [
        'Title',
        'Content',
        'Parent/Guardian\'s Name: __________________________________',
        'Parent/Guardian\'s Signature: ________________________________',
        'Date: __________________'
    ]
    
    # Extract fields
    fields = extractor.extract_consent_form_fields(text_lines)
    
    # Check that parent_guardian_signature field does NOT exist
    parent_guardian_sig_field = next(
        (f for f in fields if 'signature' in f.key.lower() and 'parent' in f.key.lower()), 
        None
    )
    
    assert parent_guardian_sig_field is None, \
        "Parent/Guardian Signature field should not be extracted"
    
    # But parent_guardian_name should exist
    parent_guardian_name_field = next(
        (f for f in fields if f.key == 'parent_guardian_name'), 
        None
    )
    
    assert parent_guardian_name_field is not None, \
        "Parent/Guardian Name field should be extracted"
    
    print("✓ Parent/Guardian Signature correctly filtered")
    return True


def test_complete_labial_frenectomy_workflow():
    """Test the complete workflow with all three fixes"""
    print("Testing complete Labial Frenectomy workflow...")
    
    extractor = ConsentFormFieldExtractor()
    
    # Realistic text lines from the document
    text_lines = [
        'Labial Frenectomy Informed Consent',
        'Patient\'s Name: \t\t\t\t\t\t\tPatient Date of Birth:',
        "The recommendation for a lip (labial) frenectomy has been made based upon your child's",
        'Symptoms and examination of their mouth. We want you to be aware of the commonly known risks.',
        '- Compromise lip mobility',
        '- Gingival (gum) recession',
        'I understand the above statements and have had my questions answered',
        "Parent/Guardian's Name: __________________________________",
        "Parent/Guardian's Signature: ________________________________",
        'Date: __________________'
    ]
    
    # Extract fields
    fields = extractor.extract_consent_form_fields(text_lines)
    
    # Verify all expected fields
    field_keys = [f.key for f in fields]
    
    # Should have: form_1, parent_guardian_name, signature, date_signed
    assert 'form_1' in field_keys, "form_1 field missing"
    assert 'parent_guardian_name' in field_keys, "parent_guardian_name field missing"
    assert 'signature' in field_keys, "signature field missing"
    assert 'date_signed' in field_keys, "date_signed field missing"
    
    # Check form_1 field (HTML content)
    form_field = next(f for f in fields if f.key == 'form_1')
    assert form_field.section == 'Labial Frenectomy Informed Consent', \
        f"Expected section 'Labial Frenectomy Informed Consent', got '{form_field.section}'"
    
    html_content = form_field.control.get('html_text', '')
    assert '{{patient_name}}' in html_content, \
        "Patient's Name placeholder not found in HTML"
    assert 'Parent/Guardian' not in html_content, \
        "Parent/Guardian should not be in HTML content"
    
    # Check parent_guardian_name field
    parent_field = next(f for f in fields if f.key == 'parent_guardian_name')
    assert parent_field.field_type == 'input', \
        f"Expected parent_guardian_name to be 'input', got '{parent_field.field_type}'"
    assert parent_field.section == 'Signature', \
        f"Expected parent_guardian_name section to be 'Signature', got '{parent_field.section}'"
    
    print("✓ Complete workflow working correctly")
    print(f"  - Section: {form_field.section}")
    print(f"  - Fields extracted: {', '.join(field_keys)}")
    return True


if __name__ == '__main__':
    print("="*80)
    print("Testing Labial Frenectomy consent form fixes")
    print("="*80)
    print()
    
    tests = [
        test_title_ending_with_informed_consent,
        test_patients_name_with_apostrophe,
        test_parent_guardian_name_field_extraction,
        test_parent_guardian_name_not_in_html,
        test_parent_guardian_signature_still_filtered,
        test_complete_labial_frenectomy_workflow
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"✗ Test failed: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ Test error: {e}")
            failed += 1
        print()
    
    print("="*80)
    print(f"Results: {passed} passed, {failed} failed")
    print("="*80)
    
    sys.exit(0 if failed == 0 else 1)
