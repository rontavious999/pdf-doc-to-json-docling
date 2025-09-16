#!/usr/bin/env python3
"""
Extract text from DOCX files using Docling to investigate what should be extracted
"""

import os
from pathlib import Path
from docling.document_converter import DocumentConverter

def extract_text_from_docx_files():
    """Extract text from all DOCX files using Docling with same model as script"""
    docx_dir = Path("/home/runner/work/pdf-doc-to-json-docling/pdf-doc-to-json-docling/docx")
    
    # Initialize converter with same settings as script
    converter = DocumentConverter()
    
    for docx_file in docx_dir.glob("*.docx"):
        print(f"\n{'='*80}")
        print(f"EXTRACTING: {docx_file.name}")
        print(f"{'='*80}")
        
        try:
            # Convert using Docling
            result = converter.convert(docx_file)
            
            # Extract all text elements
            text_lines = []
            for element in result.document.texts:
                line = element.text.strip()
                if line:
                    text_lines.append(line)
            
            print(f"Total text elements extracted: {len(text_lines)}")
            print(f"Document name: {result.document.name}")
            
            # Show all text lines
            print("\n--- RAW TEXT EXTRACTION ---")
            for i, line in enumerate(text_lines, 1):
                print(f"{i:3d}: {line}")
            
            # Analyze for potential fields
            print("\n--- FIELD ANALYSIS ---")
            potential_fields = []
            for line in text_lines:
                line_lower = line.lower()
                # Look for signature patterns
                if any(pattern in line_lower for pattern in ['signature', 'patient name', 'printed name', 'date:', 'relationship']):
                    potential_fields.append(f"SIGNATURE FIELD: {line}")
                # Look for doctor/provider patterns
                elif any(pattern in line_lower for pattern in ['dr.', 'doctor', 'consent to']):
                    potential_fields.append(f"PROVIDER FIELD: {line}")
                # Look for form content
                elif len(line) > 50:
                    potential_fields.append(f"CONTENT: {line[:100]}...")
            
            print(f"Potential fields identified: {len(potential_fields)}")
            for field in potential_fields:
                print(f"  - {field}")
                
        except Exception as e:
            print(f"Error processing {docx_file.name}: {e}")

if __name__ == "__main__":
    extract_text_from_docx_files()