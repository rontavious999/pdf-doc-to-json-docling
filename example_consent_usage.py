#!/usr/bin/env python3
"""
Example usage of the Consent Converter

This script demonstrates how to use the consent_converter module programmatically.
"""

from pathlib import Path
from consent_converter import ConsentToJSONConverter

def example_single_file():
    """Example: Convert a single consent form"""
    print("Example 1: Converting a single consent form")
    print("=" * 60)
    
    # Initialize converter
    converter = ConsentToJSONConverter()
    
    # Convert a consent form
    input_file = Path("docx/Informed Consent for Biopsy.docx")
    output_file = Path("example_output.json")
    
    if input_file.exists():
        result = converter.convert_consent_to_json(input_file, output_file)
        
        print(f"✓ Converted: {input_file.name}")
        print(f"  Output: {output_file}")
        print(f"  Fields: {result['field_count']}")
        print(f"  Sections: {result['section_count']}")
        print(f"  Valid: {result['is_valid']}")
        print(f"  Format: {result['pipeline_info']['document_format']}")
    else:
        print(f"✗ File not found: {input_file}")
    
    print()

def example_access_spec():
    """Example: Access the generated spec programmatically"""
    print("Example 2: Accessing the specification programmatically")
    print("=" * 60)
    
    converter = ConsentToJSONConverter()
    input_file = Path("docx/Informed Consent for Biopsy.docx")
    
    if input_file.exists():
        # Convert without saving to file (output_path=None)
        result = converter.convert_consent_to_json(input_file, output_path=None)
        
        # Access the spec
        spec = result['spec']
        
        print(f"Total fields: {len(spec)}")
        print("\nField breakdown:")
        
        # Group by section
        sections = {}
        for field in spec:
            section = field['section']
            if section not in sections:
                sections[section] = []
            sections[section].append(field)
        
        for section, fields in sections.items():
            print(f"\n  {section} Section: {len(fields)} fields")
            for field in fields:
                print(f"    - {field['title'] or field['key']} [{field['type']}]")
        
        # Show consent text preview
        form_field = next((f for f in spec if f['key'] == 'form_1'), None)
        if form_field:
            html_text = form_field['control'].get('html_text', '')
            preview = html_text[:200] + "..." if len(html_text) > 200 else html_text
            print(f"\nConsent text preview:")
            print(f"  {preview}")
    else:
        print(f"✗ File not found: {input_file}")
    
    print()

def example_check_provider_placeholders():
    """Example: Check if provider placeholders were applied"""
    print("Example 3: Checking provider placeholders")
    print("=" * 60)
    
    converter = ConsentToJSONConverter()
    input_file = Path("docx/Informed Consent for Biopsy.docx")
    
    if input_file.exists():
        result = converter.convert_consent_to_json(input_file, output_path=None)
        spec = result['spec']
        
        # Find the consent text field
        form_field = next((f for f in spec if f['key'] == 'form_1'), None)
        if form_field:
            html_text = form_field['control'].get('html_text', '')
            
            # Count provider placeholders
            placeholder_count = html_text.count('{{provider}}')
            
            print(f"Provider placeholders found: {placeholder_count}")
            
            if placeholder_count > 0:
                print("✓ Provider placeholder substitution was successful")
            else:
                print("✗ No provider placeholders found (may not be needed for this form)")
    else:
        print(f"✗ File not found: {input_file}")
    
    print()

if __name__ == "__main__":
    print("\nConsent Converter - Usage Examples")
    print("=" * 60)
    print()
    
    # Run examples
    example_single_file()
    example_access_spec()
    example_check_provider_placeholders()
    
    print("=" * 60)
    print("For more examples, see CONSENT_CONVERTER_README.md")
