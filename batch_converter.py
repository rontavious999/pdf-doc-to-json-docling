#!/usr/bin/env python3
"""
Batch PDF to JSON converter for Modento Forms

Process multiple PDFs in a directory
"""

import argparse
from pathlib import Path
import json
from pdf_to_json_converter import PDFToJSONConverter


def process_directory(input_dir: Path, output_dir: Path = None, verbose: bool = False):
    """Process all PDFs in a directory"""
    if output_dir is None:
        output_dir = input_dir / "json_output"
    
    output_dir.mkdir(exist_ok=True)
    
    converter = PDFToJSONConverter()
    pdf_files = list(input_dir.glob("*.pdf"))
    
    if not pdf_files:
        print(f"No PDF files found in {input_dir}")
        return
    
    print(f"Found {len(pdf_files)} PDF files to process\n")
    
    results = []
    
    for pdf_path in pdf_files:
        try:
            output_path = output_dir / f"{pdf_path.stem}.json"
            result = converter.convert_pdf_to_json(pdf_path, output_path)
            
            results.append({
                "file": pdf_path.name,
                "success": True,
                "fields": result["field_count"],
                "sections": result["section_count"],
                "valid": result["is_valid"],
                "output": str(output_path),
                "pipeline_info": result["pipeline_info"]
            })
            
            if verbose and result['errors']:
                print(f"  Validation warnings:")
                for error in result['errors']:
                    print(f"    - {error}")
        
        except Exception as e:
            print(f"Error processing {pdf_path.name}: {e}")
            results.append({
                "file": pdf_path.name,
                "success": False,
                "error": str(e)
            })
    
    # Save summary
    summary_path = output_dir / "conversion_summary.json"
    with open(summary_path, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n[✓] Summary saved to: {summary_path}")
    
    successful = sum(1 for r in results if r.get("success", False))
    print(f"[i] Successfully processed: {successful}/{len(results)} files")
    
    if verbose:
        print(f"\n[i] Pipeline details:")
        if results and results[0].get("pipeline_info"):
            pipeline = results[0]["pipeline_info"]
            print(f"    Pipeline/Backend: {pipeline.get('pipeline', 'Unknown')}/{pipeline.get('backend', 'Unknown')}")
            print(f"    OCR Engine: {pipeline.get('ocr_engine', 'Unknown')} ({'enabled' if pipeline.get('ocr_enabled') else 'disabled'})")


def main():
    parser = argparse.ArgumentParser(description="Batch convert PDFs to Modento JSON format using Docling")
    parser.add_argument("input_dir", help="Directory containing PDF files")
    parser.add_argument("--output-dir", "-o", help="Output directory for JSON files")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    input_dir = Path(args.input_dir)
    if not input_dir.exists() or not input_dir.is_dir():
        print(f"Error: Input directory not found: {input_dir}")
        return 1
    
    output_dir = Path(args.output_dir) if args.output_dir else None
    
    process_directory(input_dir, output_dir, args.verbose)
    return 0


if __name__ == "__main__":
    exit(main())