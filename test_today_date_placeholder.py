#!/usr/bin/env python3
"""
Test today_date placeholder in consent_converter.py

This test validates that:
1. "Date: ___" patterns are replaced with {{today_date}}
2. "Date of Birth:" patterns are NOT affected by the today_date replacement
3. "Date Signed:" patterns are NOT affected by the today_date replacement
"""

import sys
from pathlib import Path

# Add the parent directory to the path for imports
sys.path.insert(0, str(Path(__file__).parent))

from consent_converter import ConsentFormFieldExtractor


def test_today_date_placeholder():
    """Test that Date: ___ is replaced with {{today_date}}"""
    print("Testing today_date placeholder replacement...")
    
    extractor = ConsentFormFieldExtractor()
    
    # Test cases for Date: ___ pattern
    test_cases = [
        ("Date: _______________", "Date: {{today_date}}"),
        ("Date: _______", "Date: {{today_date}}"),
        ("date: ________", "Date: {{today_date}}"),  # case insensitive
    ]
    
    for i, (input_text, expected_output) in enumerate(test_cases, 1):
        html_content, _ = extractor._create_enhanced_consent_html(
            [input_text],
            input_text,
            []
        )
        
        if expected_output in html_content:
            print(f"✓ Test {i} passed: today_date placeholder replaced correctly")
        else:
            print(f"✗ Test {i} failed: Expected '{expected_output}' in output")
            print(f"  Got: {html_content}")
            return False
    
    print("All today_date placeholder tests passed!\n")
    return True


def test_date_of_birth_not_affected():
    """Test that Date of Birth patterns are NOT affected by today_date replacement"""
    print("Testing that Date of Birth is not affected by today_date replacement...")
    
    extractor = ConsentFormFieldExtractor()
    
    # These should use patient_dob, not today_date
    test_cases = [
        ("Date of Birth: _______________", "Date of Birth: {{patient_dob}}"),
        ("date of birth: _______", "Date of Birth: {{patient_dob}}"),
    ]
    
    for i, (input_text, expected_output) in enumerate(test_cases, 1):
        html_content, _ = extractor._create_enhanced_consent_html(
            [input_text],
            input_text,
            []
        )
        
        if expected_output in html_content and "{{today_date}}" not in html_content:
            print(f"✓ Test {i} passed: Date of Birth uses patient_dob, not today_date")
        else:
            print(f"✗ Test {i} failed: Expected '{expected_output}' and no {{{{today_date}}}}")
            print(f"  Got: {html_content}")
            return False
    
    print("Date of Birth tests passed!\n")
    return True


def test_date_signed_not_affected():
    """Test that Date Signed patterns are NOT affected by today_date replacement"""
    print("Testing that Date Signed is not affected by today_date replacement...")
    
    extractor = ConsentFormFieldExtractor()
    
    # Date Signed should remain as is (no replacement in HTML content)
    test_cases = [
        "Date Signed: _______________",
        "date signed: _______",
    ]
    
    for i, input_text in enumerate(test_cases, 1):
        html_content, _ = extractor._create_enhanced_consent_html(
            [input_text],
            input_text,
            []
        )
        
        # Date Signed should not be replaced with today_date in the content
        # (it becomes a separate field in the schema)
        if "{{today_date}}" not in html_content:
            print(f"✓ Test {i} passed: Date Signed is not replaced with today_date")
        else:
            print(f"✗ Test {i} failed: Date Signed should not use today_date")
            print(f"  Got: {html_content}")
            return False
    
    print("Date Signed tests passed!\n")
    return True


def test_combined_date_patterns():
    """Test document with multiple date patterns"""
    print("Testing document with multiple date patterns...")
    
    extractor = ConsentFormFieldExtractor()
    
    # Test with all three patterns in one document
    input_lines = [
        "Date: _______________",
        "Patient Name: {{patient_name}}",
        "Date of Birth: _______________",
        "I consent to treatment.",
    ]
    
    html_content, _ = extractor._create_enhanced_consent_html(
        input_lines,
        '\n'.join(input_lines),
        []
    )
    
    # Check all expected placeholders
    checks = [
        ("Date: {{today_date}}", "today_date placeholder"),
        ("Date of Birth: {{patient_dob}}", "patient_dob placeholder"),
        ("{{patient_name}}", "patient_name placeholder"),
    ]
    
    all_passed = True
    for expected, description in checks:
        if expected in html_content:
            print(f"✓ {description} found correctly")
        else:
            print(f"✗ {description} NOT found")
            print(f"  Content: {html_content}")
            all_passed = False
    
    if all_passed:
        print("Combined date patterns test passed!\n")
    
    return all_passed


def main():
    """Run all tests"""
    print("Running today_date placeholder tests...\n")
    print("=" * 70)
    print()
    
    tests = [
        test_today_date_placeholder,
        test_date_of_birth_not_affected,
        test_date_signed_not_affected,
        test_combined_date_patterns,
    ]
    
    results = []
    for test in tests:
        try:
            results.append(test())
        except Exception as e:
            print(f"✗ Test failed with exception: {e}")
            import traceback
            traceback.print_exc()
            results.append(False)
    
    print("=" * 70)
    if all(results):
        print("🎉 All tests passed!")
        print("\nSummary:")
        print("- Date: ___ is replaced with {{today_date}}")
        print("- Date of Birth: ___ uses {{patient_dob}} (not affected)")
        print("- Date Signed: ___ is handled separately (not affected)")
        return 0
    else:
        print("❌ Some tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
