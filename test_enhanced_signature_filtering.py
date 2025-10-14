#!/usr/bin/env python3
"""
Test enhanced signature filtering in consent_converter.py

This test validates that:
1. Witness signature lines are properly filtered (including apostrophe variations)
2. Doctor signature lines are properly filtered (including apostrophe variations)
3. Parent/Guardian signature lines are properly filtered
4. Lines with only underscores are properly filtered
"""

import sys
from pathlib import Path

# Add the parent directory to the path for imports
sys.path.insert(0, str(Path(__file__).parent))

from consent_converter import ConsentFormFieldExtractor


def test_witness_apostrophe_filtering():
    """Test that witness lines with apostrophes are filtered"""
    print("Testing witness signature filtering with apostrophes...")
    
    extractor = ConsentFormFieldExtractor()
    
    test_lines = [
        "Witness's Signature Date",
        "Witness\u2019s Signature Date",  # Unicode right single quotation mark
        "Patient Name: {{patient_name}}",  # Should be kept
    ]
    
    filtered_content = "<br>".join(test_lines)
    filtered_content = extractor._remove_witness_and_doctor_signatures(filtered_content)
    
    if "Witness" not in filtered_content and "{{patient_name}}" in filtered_content:
        print("✓ Witness lines with apostrophes are filtered correctly")
        return True
    else:
        print("✗ Failed: Witness lines not properly filtered")
        print(f"  Content: {filtered_content}")
        return False


def test_doctor_apostrophe_filtering():
    """Test that doctor lines with apostrophes are filtered"""
    print("Testing doctor signature filtering with apostrophes...")
    
    extractor = ConsentFormFieldExtractor()
    
    test_lines = [
        "Doctor's Signature Date",
        "Doctor\u2019s Signature Date",  # Unicode right single quotation mark
        "Patient Signature: ___",  # Should be kept
    ]
    
    filtered_content = "<br>".join(test_lines)
    filtered_content = extractor._remove_witness_and_doctor_signatures(filtered_content)
    
    if "Doctor" not in filtered_content and "Patient Signature" in filtered_content:
        print("✓ Doctor lines with apostrophes are filtered correctly")
        return True
    else:
        print("✗ Failed: Doctor lines not properly filtered")
        print(f"  Content: {filtered_content}")
        return False


def test_parent_guardian_filtering():
    """Test that parent/guardian signature lines are filtered"""
    print("Testing parent/guardian signature filtering...")
    
    extractor = ConsentFormFieldExtractor()
    
    test_lines = [
        "Patient/Parent/Guardian Signature Date",
        "Patient/Parent/Guardian Name (Print) Witness",
        "Parent's Signature",
        "Guardian's Signature",
        "Legal Guardian's Signature",
        "Patient Name: {{patient_name}}",  # Should be kept
    ]
    
    filtered_content = "<br>".join(test_lines)
    filtered_content = extractor._remove_witness_and_doctor_signatures(filtered_content)
    
    checks = [
        ("Patient/Parent/Guardian" not in filtered_content, "Patient/Parent/Guardian lines"),
        ("Parent's Signature" not in filtered_content, "Parent's Signature"),
        ("Guardian's Signature" not in filtered_content, "Guardian's Signature"),
        ("{{patient_name}}" in filtered_content, "Patient name preserved"),
    ]
    
    all_passed = True
    for check, description in checks:
        if check:
            print(f"  ✓ {description} filtered correctly")
        else:
            print(f"  ✗ {description} NOT filtered correctly")
            all_passed = False
    
    if not all_passed:
        print(f"  Content: {filtered_content}")
    
    return all_passed


def test_underscore_line_filtering():
    """Test that lines with mostly underscores are filtered"""
    print("Testing underscore line filtering...")
    
    extractor = ConsentFormFieldExtractor()
    
    test_lines = [
        "____________________________________________",
        "____________________________________________ _______________________",
        "Patient Name: ___",  # Should be kept (not mostly underscores after Patient Name:)
        "Regular consent text here",  # Should be kept
    ]
    
    filtered_content = "<br>".join(test_lines)
    filtered_content = extractor._remove_witness_and_doctor_signatures(filtered_content)
    
    # Count how many underscore lines remain
    underscore_lines = [line for line in filtered_content.split("<br>") if "_" * 10 in line]
    
    # Only "Patient Name: ___" should remain (as it has actual field label)
    # Pure underscore lines should be filtered
    if len(underscore_lines) <= 1 and "Patient Name" in filtered_content and "Regular consent text" in filtered_content:
        print("✓ Underscore lines are filtered correctly")
        return True
    else:
        print("✗ Failed: Underscore lines not properly filtered")
        print(f"  Remaining underscore lines: {len(underscore_lines)}")
        print(f"  Content: {filtered_content}")
        return False


def test_complex_document():
    """Test with a complex document containing multiple signature patterns"""
    print("Testing complex document with multiple patterns...")
    
    extractor = ConsentFormFieldExtractor()
    
    input_lines = [
        "Date: _______________",
        "Patient Name: {{patient_name}} Date of Birth: {{patient_dob}}",
        "I consent to treatment.",
        "____________________________________________ _______________________",
        "Patient/Parent/Guardian Signature Date",
        "____________________________________________ ________________________",
        "Patient/Parent/Guardian Name (Print) Witness",
        "____________________________________________",
        "Doctor's Signature Date",
    ]
    
    html_content, _ = extractor._create_enhanced_consent_html(
        input_lines,
        '\n'.join(input_lines),
        []
    )
    
    checks = [
        ("Date: {{today_date}}" in html_content, "today_date placeholder"),
        ("{{patient_name}}" in html_content, "patient_name placeholder"),
        ("{{patient_dob}}" in html_content, "patient_dob placeholder"),
        ("I consent to treatment" in html_content, "consent text preserved"),
        ("Patient/Parent/Guardian" not in html_content, "Patient/Parent/Guardian filtered"),
        ("Witness" not in html_content.lower(), "Witness filtered"),
        ("Doctor's Signature" not in html_content, "Doctor's Signature filtered"),
    ]
    
    all_passed = True
    for check, description in checks:
        if check:
            print(f"  ✓ {description}")
        else:
            print(f"  ✗ {description}")
            all_passed = False
    
    if not all_passed:
        print(f"  Content: {html_content}")
    
    return all_passed


def main():
    """Run all tests"""
    print("Running enhanced signature filtering tests...\n")
    print("=" * 70)
    print()
    
    tests = [
        test_witness_apostrophe_filtering,
        test_doctor_apostrophe_filtering,
        test_parent_guardian_filtering,
        test_underscore_line_filtering,
        test_complex_document,
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
            print()
        except Exception as e:
            print(f"✗ Test failed with exception: {e}")
            import traceback
            traceback.print_exc()
            results.append(False)
            print()
    
    print("=" * 70)
    if all(results):
        print("🎉 All tests passed!")
        print("\nSummary:")
        print("- Witness signature lines (with apostrophes) are filtered")
        print("- Doctor signature lines (with apostrophes) are filtered")
        print("- Parent/Guardian signature lines are filtered")
        print("- Lines with mostly underscores are filtered")
        print("- Patient fields and consent text are preserved")
        return 0
    else:
        print("❌ Some tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
