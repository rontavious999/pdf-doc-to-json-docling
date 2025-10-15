#!/usr/bin/env python3
"""
Test hash marker removal and title case conversion in consent_converter.py

This test validates that:
1. Standalone # markers (empty headers) are removed from HTML content
2. Titles starting with # are detected and used as section names
3. Titles are converted to proper title case
"""

import sys
from pathlib import Path

# Add the parent directory to the path for imports
sys.path.insert(0, str(Path(__file__).parent))

from consent_converter import ConsentFormFieldExtractor, ConsentShapingManager


def test_standalone_hash_removal():
    """Test that standalone # markers are removed from content"""
    print("Testing standalone # marker removal...")
    
    extractor = ConsentFormFieldExtractor()
    
    # Test case with standalone # marker followed by actual title
    consent_lines = [
        '# ',  # Standalone empty header
        '# Informed refusal of necessary x-rays',
        'Patient Name: {{patient_name}}'
    ]
    
    html_content, detected_title = extractor._create_enhanced_consent_html(
        consent_lines,
        '\n'.join(consent_lines),
        []  # No provider patterns for this test
    )
    
    # Check that standalone # was removed (not present in HTML)
    if '#<br>' in html_content or '# <br>' in html_content:
        print(f"✗ Failed: Standalone # marker was not removed")
        print(f"  Content: {html_content[:200]}")
        return False
    
    print(f"✓ Standalone # marker removal test passed")
    return True


def test_single_hash_title_detection():
    """Test that titles starting with single # are detected"""
    print("Testing single # title detection...")
    
    extractor = ConsentFormFieldExtractor()
    
    # Test case with single # title
    consent_lines = [
        '# Informed refusal of necessary x-rays',
        'Patient Name: {{patient_name}}'
    ]
    
    html_content, detected_title = extractor._create_enhanced_consent_html(
        consent_lines,
        '\n'.join(consent_lines),
        []
    )
    
    # Check that title was detected
    if detected_title != 'Informed refusal of necessary x-rays':
        print(f"✗ Failed: Title was not detected correctly")
        print(f"  Expected: 'Informed refusal of necessary x-rays'")
        print(f"  Got: {detected_title}")
        return False
    
    # Check that # was removed from the title in HTML
    if '#' in html_content:
        print(f"✗ Failed: # character still present in HTML")
        print(f"  Content: {html_content[:200]}")
        return False
    
    print(f"✓ Single # title detection test passed")
    return True


def test_title_case_conversion():
    """Test that titles are converted to proper title case"""
    print("Testing title case conversion...")
    
    shaper = ConsentShapingManager()
    
    test_cases = [
        {
            'input': 'Informed refusal of necessary x-rays',
            'expected': 'Informed Refusal of Necessary X-Rays'
        },
        {
            'input': 'tooth removal consent form',
            'expected': 'Tooth Removal Consent Form'
        },
        {
            'input': 'INFORMED CONSENT FOR BONE GRAFTING',
            'expected': 'Informed Consent for Bone Grafting'
        },
        {
            'input': 'labial frenectomy informed consent',
            'expected': 'Labial Frenectomy Informed Consent'
        }
    ]
    
    all_passed = True
    for i, test_case in enumerate(test_cases):
        result = shaper.to_title_case(test_case['input'])
        if result == test_case['expected']:
            print(f"  ✓ Test {i+1} passed: '{test_case['input']}' → '{result}'")
        else:
            print(f"  ✗ Test {i+1} failed: '{test_case['input']}'")
            print(f"    Expected: '{test_case['expected']}'")
            print(f"    Got: '{result}'")
            all_passed = False
    
    if all_passed:
        print(f"✓ Title case conversion tests passed")
    
    return all_passed


def test_hyphenated_words_in_title_case():
    """Test that hyphenated words are properly capitalized in title case"""
    print("Testing hyphenated words in title case...")
    
    shaper = ConsentShapingManager()
    
    test_cases = [
        {
            'input': 'Informed refusal of necessary x-rays',
            'expected': 'Informed Refusal of Necessary X-Rays'
        },
        {
            'input': 'post-operative care instructions',
            'expected': 'Post-Operative Care Instructions'
        },
        {
            'input': 'pre-treatment consultation',
            'expected': 'Pre-Treatment Consultation'
        }
    ]
    
    all_passed = True
    for i, test_case in enumerate(test_cases):
        result = shaper.to_title_case(test_case['input'])
        if result == test_case['expected']:
            print(f"  ✓ Test {i+1} passed: '{test_case['input']}' → '{result}'")
        else:
            print(f"  ✗ Test {i+1} failed: '{test_case['input']}'")
            print(f"    Expected: '{test_case['expected']}'")
            print(f"    Got: '{result}'")
            all_passed = False
    
    if all_passed:
        print(f"✓ Hyphenated words in title case tests passed")
    
    return all_passed


def test_empty_header_lines_filtering():
    """Test that multiple empty header lines are filtered out"""
    print("Testing empty header lines filtering...")
    
    extractor = ConsentFormFieldExtractor()
    
    # Test case with multiple empty headers
    consent_lines = [
        '# ',
        '## ',
        '### ',
        '# Actual title',
        'Content line'
    ]
    
    html_content, detected_title = extractor._create_enhanced_consent_html(
        consent_lines,
        '\n'.join(consent_lines),
        []
    )
    
    # Check that the title was detected (after empty headers were filtered)
    if detected_title != 'Actual title':
        print(f"✗ Failed: Title was not detected correctly after filtering empty headers")
        print(f"  Expected: 'Actual title'")
        print(f"  Got: {detected_title}")
        return False
    
    # Check that no # markers remain in HTML
    if '#' in html_content:
        print(f"✗ Failed: # characters still present in HTML")
        print(f"  Content: {html_content[:200]}")
        return False
    
    print(f"✓ Empty header lines filtering test passed")
    return True


def main():
    """Run all tests"""
    print("Running hash marker removal and title case tests...\n")
    print("=" * 70)
    print()
    
    all_passed = True
    
    try:
        if not test_standalone_hash_removal():
            all_passed = False
        print()
        
        if not test_single_hash_title_detection():
            all_passed = False
        print()
        
        if not test_title_case_conversion():
            all_passed = False
        print()
        
        if not test_hyphenated_words_in_title_case():
            all_passed = False
        print()
        
        if not test_empty_header_lines_filtering():
            all_passed = False
        print()
        
        print("=" * 70)
        if all_passed:
            print("🎉 All tests passed!")
            print("\nSummary:")
            print("- Standalone # markers are removed from HTML content")
            print("- Titles starting with # are detected correctly")
            print("- Titles are converted to proper title case")
            print("- Hyphenated words are properly capitalized")
            print("- Empty header lines are filtered out")
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
