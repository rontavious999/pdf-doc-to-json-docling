#!/usr/bin/env python3
"""
Demo script showing the PDF and DOCX to JSON conversion capabilities
"""

from pdf_to_json_converter import DocumentToJSONConverter
from pathlib import Path
import json


def demo():
    """Demonstrate the PDF and DOCX to JSON conversion with Docling"""
    print("PDF and DOCX to Modento Forms JSON Converter Demo (Enhanced with Docling)")
    print("=" * 75)
    
    converter = DocumentToJSONConverter()
    
    # List available PDFs and DOCX files
    pdf_dir = Path("pdfs")
    test_docs_dir = Path("test_docs")
    
    pdf_files = list(pdf_dir.glob("*.pdf")) if pdf_dir.exists() else []
    docx_files = list(test_docs_dir.glob("*.docx")) if test_docs_dir.exists() else []
    
    all_files = pdf_files + docx_files
    
    if not all_files:
        print("No PDF or DOCX files found in pdfs/ or test_docs/ directories")
        return
    
    # Display file counts by type
    print(f"Found {len(all_files)} files:")
    if pdf_files:
        print(f"  PDF files ({len(pdf_files)}):")
        for pdf in pdf_files:
            print(f"    - {pdf.name}")
    if docx_files:
        print(f"  DOCX files ({len(docx_files)}):")
        for docx in docx_files:
            print(f"    - {docx.name}")
    
    print("\nProcessing first file as example...")
    sample_file = all_files[0]
    file_type = "DOCX" if sample_file.suffix.lower() in ['.docx', '.doc'] else "PDF"
    
    try:
        import time
        start_time = time.time()
        result = converter.convert_document_to_json(sample_file)
        processing_time = time.time() - start_time
        
        print(f"\nResults for {sample_file.name} ({file_type}):")
        print(f"  - Processing time: {processing_time:.3f} seconds")
        print(f"  - Fields detected: {result['field_count']}")
        print(f"  - Sections detected: {result['section_count']}")
        print(f"  - Schema valid: {result['is_valid']}")
        
        # Show pipeline info
        pipeline = result['pipeline_info']
        print(f"  - Pipeline: {pipeline['pipeline']}")
        print(f"  - Backend: {pipeline['backend']}")
        print(f"  - Document format: {pipeline.get('document_format', 'PDF')}")
        
        if pipeline.get('ocr_used'):
            print(f"  - OCR Engine: {pipeline['ocr_engine']} (used)")
        else:
            print(f"  - OCR: not required (native text extraction)")
        
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