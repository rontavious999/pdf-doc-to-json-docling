#!/usr/bin/env python3
"""
Demo script showing the PDF to JSON conversion capabilities
"""

from pdf_to_json_converter import PDFToJSONConverter
from pathlib import Path
import json


def demo():
    """Demonstrate the PDF to JSON conversion with Docling"""
    print("PDF to Modento Forms JSON Converter Demo (Enhanced with Docling)")
    print("=" * 65)
    
    converter = PDFToJSONConverter()
    
    # List available PDFs
    pdf_dir = Path("pdfs")
    pdf_files = list(pdf_dir.glob("*.pdf"))
    
    if not pdf_files:
        print("No PDF files found in pdfs/ directory")
        return
    
    print(f"Found {len(pdf_files)} PDF files:")
    for i, pdf in enumerate(pdf_files, 1):
        print(f"  {i}. {pdf.name}")
    
    print("\nProcessing first PDF as example...")
    sample_pdf = pdf_files[0]
    
    try:
        result = converter.convert_pdf_to_json(sample_pdf)
        
        print(f"\nResults for {sample_pdf.name}:")
        print(f"  - Fields detected: {result['field_count']}")
        print(f"  - Sections detected: {result['section_count']}")
        print(f"  - Schema valid: {result['is_valid']}")
        
        # Show pipeline info
        pipeline = result['pipeline_info']
        print(f"  - Pipeline: {pipeline['pipeline']}")
        print(f"  - Backend: {pipeline['backend']}")
        print(f"  - OCR Engine: {pipeline['ocr_engine']} ({'enabled' if pipeline['ocr_enabled'] else 'disabled'})")
        
        if result['errors']:
            print(f"  - Warnings: {len(result['errors'])}")
        
        # Show sample fields
        spec = result['spec']
        print(f"\nSample fields (first 3):")
        for i, field in enumerate(spec[:3]):
            print(f"  {i+1}. {field['title']} [{field['type']}] - {field['section']}")
        
        # Show sections
        sections = set(field['section'] for field in spec)
        print(f"\nSections detected: {', '.join(sorted(sections))}")
        
        # Save demo output
        demo_output = Path("demo_output.json")
        with open(demo_output, 'w') as f:
            json.dump(spec, f, indent=2)
        print(f"\nFull output saved to: {demo_output}")
        
        print("\n✓ Conversion completed successfully with Docling's advanced capabilities!")
        
    except Exception as e:
        print(f"\nError during conversion: {e}")


if __name__ == "__main__":
    demo()