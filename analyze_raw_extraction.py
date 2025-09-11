#!/usr/bin/env python3
"""
Analyze raw text extraction from PDFs using Docling to understand 
what text is being extracted and how it should be processed.
"""

from pathlib import Path
from docling.document_converter import DocumentConverter
from docling.datamodel.pipeline_options import PdfPipelineOptions

def extract_and_analyze_pdf(pdf_path: Path, output_dir: Path):
    """Extract raw text from PDF and save for analysis"""
    
    # Configure Docling for same settings as main script
    pipeline_options = PdfPipelineOptions()
    pipeline_options.do_ocr = True
    pipeline_options.do_table_structure = True
    pipeline_options.images_scale = 2.0
    pipeline_options.generate_page_images = False
    pipeline_options.generate_table_images = False
    pipeline_options.generate_picture_images = False
    
    converter = DocumentConverter()
    
    print(f"Extracting text from {pdf_path.name}...")
    
    # Convert PDF
    result = converter.convert(str(pdf_path))
    full_text = result.document.export_to_text()
    
    # Save raw text
    text_output_path = output_dir / f"{pdf_path.stem}_raw_text.txt"
    with open(text_output_path, 'w', encoding='utf-8') as f:
        f.write(full_text)
    
    # Analyze text structure
    lines = [line.strip() for line in full_text.split('\n') if line.strip()]
    
    analysis_output_path = output_dir / f"{pdf_path.stem}_analysis.txt"
    with open(analysis_output_path, 'w', encoding='utf-8') as f:
        f.write(f"=== Analysis of {pdf_path.name} ===\n\n")
        f.write(f"Total lines: {len(lines)}\n")
        f.write(f"Total characters: {len(full_text)}\n\n")
        
        f.write("=== First 50 lines ===\n")
        for i, line in enumerate(lines[:50]):
            f.write(f"{i+1:3d}: {line}\n")
        
        f.write("\n=== Lines containing underscores (potential fields) ===\n")
        field_lines = [(i+1, line) for i, line in enumerate(lines) if '_' in line and len(line) > 5]
        for line_num, line in field_lines[:30]:  # First 30 field lines
            f.write(f"{line_num:3d}: {line}\n")
        
        f.write("\n=== Lines containing colons (potential labels) ===\n")
        label_lines = [(i+1, line) for i, line in enumerate(lines) if ':' in line and len(line) < 100]
        for line_num, line in label_lines[:20]:  # First 20 label lines
            f.write(f"{line_num:3d}: {line}\n")
        
        f.write(f"\n=== Sections/Headers (lines with specific patterns) ===\n")
        section_lines = []
        for i, line in enumerate(lines):
            line_upper = line.upper()
            if (line.startswith('##') or 
                any(keyword in line_upper for keyword in [
                    'PATIENT INFORMATION', 'MEDICAL HISTORY', 'DENTAL HISTORY', 
                    'INSURANCE', 'EMERGENCY CONTACT', 'SIGNATURE', 'CONSENT',
                    'FOR CHILDREN', 'MINORS ONLY', 'PRIMARY DENTAL', 
                    'SECONDARY DENTAL', 'BENEFIT PLAN'
                ])):
                section_lines.append((i+1, line))
        
        for line_num, line in section_lines:
            f.write(f"{line_num:3d}: {line}\n")
    
    print(f"Saved raw text to: {text_output_path}")
    print(f"Saved analysis to: {analysis_output_path}")
    
    return lines

def main():
    """Analyze all PDFs in the pdfs directory"""
    pdfs_dir = Path("pdfs")
    output_dir = Path("text_analysis")
    output_dir.mkdir(exist_ok=True)
    
    pdf_files = list(pdfs_dir.glob("*.pdf"))
    
    print(f"Found {len(pdf_files)} PDF files to analyze\n")
    
    for pdf_path in pdf_files:
        try:
            lines = extract_and_analyze_pdf(pdf_path, output_dir)
            print(f"✓ {pdf_path.name}: {len(lines)} lines extracted\n")
        except Exception as e:
            print(f"✗ Error processing {pdf_path.name}: {e}\n")
    
    print(f"Analysis complete. Check {output_dir} for results.")

if __name__ == "__main__":
    main()