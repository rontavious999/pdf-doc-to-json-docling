#!/usr/bin/env python3
"""
Test bold markdown title detection in consent_converter.py

This test validates that bold markdown titles (e.g., **Title**) are correctly
detected and used as section names in consent forms.
"""

import sys
from pathlib import Path

# Add the parent directory to the path for imports
sys.path.insert(0, str(Path(__file__).parent))

from consent_converter import ConsentFormFieldExtractor


def test_bold_markdown_title_detection():
    """Test that bold markdown titles are correctly detected"""
    print("Testing bold markdown title detection...")
    
    extractor = ConsentFormFieldExtractor()
    
    # Test case 1: Bold markdown title
    test_lines_1 = [
        "**Olympia Hills Family Dental Warranty Document**",
        "",
        "This is the content of the warranty document."
    ]
    
    html_1, title_1 = extractor._create_enhanced_consent_html(
        test_lines_1, 
        " ".join(test_lines_1), 
        []
    )
    
    assert title_1 == "Olympia Hills Family Dental Warranty Document", \
        f"Expected 'Olympia Hills Family Dental Warranty Document', got '{title_1}'"
    assert "Olympia Hills Family Dental Warranty Document" in html_1, \
        "Title should be in HTML content"
    print("✓ Test 1 passed: Bold markdown title detected correctly")
    
    # Test case 2: Bold markdown title with mixed case
    test_lines_2 = [
        "**Treatment Authorization Document**",
        "",
        "Patient consent for treatment."
    ]
    
    html_2, title_2 = extractor._create_enhanced_consent_html(
        test_lines_2,
        " ".join(test_lines_2),
        []
    )
    
    assert title_2 == "Treatment Authorization Document", \
        f"Expected 'Treatment Authorization Document', got '{title_2}'"
    print("✓ Test 2 passed: Mixed case bold title detected correctly")
    
    # Test case 3: Long bold text (should not be treated as title)
    test_lines_3 = [
        "**This is a very long paragraph that happens to be bold but should not be treated as a title because it is too long and exceeds the reasonable title length threshold of 150 characters and continues on**",
        "",
        "More content here."
    ]
    
    html_3, title_3 = extractor._create_enhanced_consent_html(
        test_lines_3,
        " ".join(test_lines_3),
        []
    )
    
    assert title_3 is None, \
        f"Long bold text should not be detected as title, got '{title_3}'"
    print("✓ Test 3 passed: Long bold text not treated as title")
    
    # Test case 4: Existing pattern - "Informed Consent for" should still work
    test_lines_4 = [
        "Informed Consent for Tooth Extraction",
        "",
        "Consent content here."
    ]
    
    html_4, title_4 = extractor._create_enhanced_consent_html(
        test_lines_4,
        " ".join(test_lines_4),
        []
    )
    
    assert title_4 == "Informed Consent for Tooth Extraction", \
        f"Expected 'Informed Consent for Tooth Extraction', got '{title_4}'"
    print("✓ Test 4 passed: Existing 'Informed Consent for' pattern still works")
    
    # Test case 5: All caps consent title should still work
    test_lines_5 = [
        "TOOTH REMOVAL CONSENT FORM",
        "",
        "Consent details."
    ]
    
    html_5, title_5 = extractor._create_enhanced_consent_html(
        test_lines_5,
        " ".join(test_lines_5),
        []
    )
    
    assert title_5 == "TOOTH REMOVAL CONSENT FORM", \
        f"Expected 'TOOTH REMOVAL CONSENT FORM', got '{title_5}'"
    print("✓ Test 5 passed: All caps consent title still works")
    
    # Test case 6: Markdown header (##) should still work
    test_lines_6 = [
        "## Dental Warranty Agreement",
        "",
        "Agreement details."
    ]
    
    html_6, title_6 = extractor._create_enhanced_consent_html(
        test_lines_6,
        " ".join(test_lines_6),
        []
    )
    
    assert title_6 == "Dental Warranty Agreement", \
        f"Expected 'Dental Warranty Agreement', got '{title_6}'"
    print("✓ Test 6 passed: Markdown header (##) still works")
    
    print("\n" + "="*70)
    print("🎉 All bold title detection tests passed!")
    print("\nSummary:")
    print("- Bold markdown titles (**Title**) are correctly detected")
    print("- Long bold text is not treated as title")
    print("- Existing title patterns still work correctly")
    print("="*70)


if __name__ == "__main__":
    try:
        test_bold_markdown_title_detection()
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
