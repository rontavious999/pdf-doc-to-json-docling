#!/usr/bin/env python3
"""
Integration test for custom placeholders in consent_converter.py

This test validates the end-to-end functionality with simulated consent content.
"""

import sys
from pathlib import Path

# Add the parent directory to the path for imports
sys.path.insert(0, str(Path(__file__).parent))

from consent_converter import ConsentFormFieldExtractor


def test_full_extraction_with_placeholders():
    """Test complete extraction process with custom placeholders"""
    print("Testing full extraction with custom placeholders...")
    
    extractor = ConsentFormFieldExtractor()
    
    # Simulate consent form with various placeholder patterns
    consent_text_lines = [
        "INFORMED CONSENT FOR DENTAL PROCEDURE",
        "",
        "Planned Procedure: _____________________",
        "",
        "Diagnosis: _____________________",
        "",
        "Alternative Treatment: _____________________",
        "",
        "I hereby consent to the dental procedure as described above.",
        "I understand the risks and benefits of the treatment.",
        "",
        "Patient Signature:",
        "Patient Name: _____________________",
        "Date of Birth: _____________________",
        "Date Signed: _____________________",
        "",
        "Witness Signature: _____________________",
        "Doctor Signature: _____________________"
    ]
    
    # Extract fields
    fields = extractor.extract_consent_form_fields(consent_text_lines)
    
    print(f"✓ Extracted {len(fields)} fields")
    
    # Find the consent text field
    consent_field = next((f for f in fields if f.key == 'form_1'), None)
    
    if not consent_field:
        print("✗ Failed: No consent text field found")
        return False
    
    html_text = consent_field.control.get('html_text', '')
    
    # Check for custom placeholders
    placeholders_found = []
    if '{{planned_procedure}}' in html_text:
        placeholders_found.append('planned_procedure')
        print("✓ Found {{planned_procedure}} placeholder")
    else:
        print("✗ Missing {{planned_procedure}} placeholder")
    
    if '{{diagnosis}}' in html_text:
        placeholders_found.append('diagnosis')
        print("✓ Found {{diagnosis}} placeholder")
    else:
        print("✗ Missing {{diagnosis}} placeholder")
    
    if '{{alternative_treatment}}' in html_text:
        placeholders_found.append('alternative_treatment')
        print("✓ Found {{alternative_treatment}} placeholder")
    else:
        print("✗ Missing {{alternative_treatment}} placeholder")
    
    # Check that witness and doctor signatures are NOT in the HTML
    if 'Witness Signature' in html_text:
        print("✗ Failed: Witness Signature should have been removed from HTML")
        return False
    else:
        print("✓ Witness Signature correctly removed from HTML")
    
    if 'Doctor Signature' in html_text:
        print("✗ Failed: Doctor Signature should have been removed from HTML")
        return False
    else:
        print("✓ Doctor Signature correctly removed from HTML")
    
    # Check that no witness or doctor signature fields were extracted
    field_keys = [f.key for f in fields]
    
    witness_fields = [key for key in field_keys if 'witness' in key.lower()]
    if witness_fields:
        print(f"✗ Failed: Found witness fields: {witness_fields}")
        return False
    else:
        print("✓ No witness fields extracted")
    
    doctor_sig_fields = [key for key in field_keys if 'doctor' in key.lower() and 'signature' in key.lower()]
    if doctor_sig_fields:
        print(f"✗ Failed: Found doctor signature fields: {doctor_sig_fields}")
        return False
    else:
        print("✓ No doctor signature fields extracted")
    
    # Verify that patient fields ARE present
    if 'signature' not in field_keys:
        print("✗ Failed: Patient signature field missing")
        return False
    else:
        print("✓ Patient signature field present")
    
    if 'date_signed' not in field_keys:
        print("✗ Failed: Date signed field missing")
        return False
    else:
        print("✓ Date signed field present")
    
    if len(placeholders_found) == 3:
        print(f"\n✓ All custom placeholders working correctly")
        return True
    else:
        print(f"\n✗ Only {len(placeholders_found)} of 3 custom placeholders found")
        return False


def main():
    """Run integration test"""
    print("Running integration test for custom placeholders...\n")
    print("=" * 70)
    print()
    
    try:
        if test_full_extraction_with_placeholders():
            print("\n" + "=" * 70)
            print("🎉 Integration test passed!")
            print("\nVerified:")
            print("- Custom placeholders (planned_procedure, diagnosis, alternative_treatment)")
            print("- Witness and doctor signatures excluded from HTML content")
            print("- Witness and doctor signature fields not extracted")
            print("- Patient fields correctly extracted")
        else:
            print("\n" + "=" * 70)
            print("❌ Integration test failed")
            sys.exit(1)
    except Exception as e:
        print(f"❌ Test error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
