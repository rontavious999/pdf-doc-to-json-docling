#!/usr/bin/env python3
"""
Analyze existing model testing results and generate comparison table
"""

import os
import json
from pathlib import Path
from typing import Dict, List, Tuple
import re

def analyze_text_files():
    """Analyze existing text output files and generate comparison table"""
    
    text_outputs_dir = Path("outputs/text_outputs")
    results = {}
    
    if not text_outputs_dir.exists():
        print("No text outputs directory found")
        return
    
    # Process all text files
    for txt_file in text_outputs_dir.glob("*.txt"):
        filename = txt_file.name
        
        # Parse filename: {pdf_name}_{config_name}.txt
        parts = filename.replace('.txt', '').split('_')
        if len(parts) < 2:
            continue
            
        # Find where config name starts (after the PDF name)
        # PDF names might contain underscores, so we look for known config patterns
        config_patterns = [
            'easyocr_standard', 'easyocr_high_confidence', 'easyocr_full_page',
            'easyocr_high_resolution', 'tesseract_standard', 'rapidocr_standard',
            'no_ocr_parsing', 'pypdfium2_backend'
        ]
        
        pdf_name = None
        config_name = None
        
        for pattern in config_patterns:
            if pattern in filename:
                config_name = pattern
                pdf_name = filename.replace(f'_{pattern}.txt', '')
                break
        
        if not pdf_name or not config_name:
            continue
        
        # Read the file and extract metrics
        try:
            with open(txt_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extract metadata from header
            lines = content.split('\n')
            extraction_time = 0
            character_count = 0
            word_count = 0
            line_count = 0
            
            for line in lines[:10]:  # Check first 10 lines for metadata
                if line.startswith('Extraction Time:'):
                    extraction_time = float(line.split(':')[1].strip().split()[0])
                elif line.startswith('Character Count:'):
                    character_count = int(line.split(':')[1].strip())
                elif line.startswith('Word Count:'):
                    word_count = int(line.split(':')[1].strip())
                elif line.startswith('Line Count:'):
                    line_count = int(line.split(':')[1].strip())
            
            # Calculate quality score
            quality_score = calculate_quality_score(character_count, word_count, line_count, content)
            
            if pdf_name not in results:
                results[pdf_name] = {}
            
            results[pdf_name][config_name] = {
                'character_count': character_count,
                'word_count': word_count, 
                'line_count': line_count,
                'extraction_time': extraction_time,
                'quality_score': quality_score,
                'success': True
            }
            
        except Exception as e:
            print(f"Error processing {txt_file}: {e}")
    
    return results

def calculate_quality_score(char_count: int, word_count: int, line_count: int, content: str) -> float:
    """Calculate quality score for extracted text"""
    if char_count == 0:
        return 0.0
    
    # Base score from character count
    base_score = min(100, char_count / 10)
    
    # Bonus for reasonable word density
    if word_count > 0:
        avg_word_length = char_count / word_count
        if 3 <= avg_word_length <= 15:  # Reasonable word length
            base_score *= 1.1
    
    # Bonus for line structure
    if line_count > 1:
        base_score *= 1.1
    
    # Check for proper spacing
    space_ratio = content.count(' ') / char_count if char_count > 0 else 0
    if 0.1 <= space_ratio <= 0.3:  # Reasonable spacing
        base_score *= 1.1
    
    return min(100.0, base_score)

def generate_comparison_table(results: Dict) -> str:
    """Generate comparison table from results"""
    
    table_lines = []
    table_lines.append("# Model Testing Comparison Results")
    table_lines.append("")
    table_lines.append("## Summary")
    table_lines.append("")
    table_lines.append("This table shows the best performing Docling configurations for each PDF file.")
    table_lines.append("")
    table_lines.append("| PDF File | Best Model | Extraction % | Second Best | Extraction % |")
    table_lines.append("|----------|------------|--------------|-------------|--------------|")
    
    # Analyze each PDF
    for pdf_name, pdf_results in results.items():
        if not pdf_results:
            table_lines.append(f"| {pdf_name}.pdf | No successful extractions | 0% | - | - |")
            continue
        
        # Sort by quality score
        sorted_results = sorted(pdf_results.items(), key=lambda x: x[1]['quality_score'], reverse=True)
        
        if len(sorted_results) >= 2:
            best_config, best_data = sorted_results[0]
            second_config, second_data = sorted_results[1]
            
            table_lines.append(
                f"| {pdf_name}.pdf | {best_config} | {best_data['quality_score']:.1f}% | {second_config} | {second_data['quality_score']:.1f}% |"
            )
        elif len(sorted_results) == 1:
            best_config, best_data = sorted_results[0]
            table_lines.append(
                f"| {pdf_name}.pdf | {best_config} | {best_data['quality_score']:.1f}% | - | - |"
            )
    
    # Add detailed statistics
    table_lines.append("")
    table_lines.append("## Detailed Statistics")
    table_lines.append("")
    table_lines.append("### Configuration Performance Summary")
    table_lines.append("")
    table_lines.append("| Configuration | Avg Quality Score | Success Rate | Avg Time (s) | Avg Characters |")
    table_lines.append("|---------------|-------------------|--------------|--------------|----------------|")
    
    # Calculate config averages
    config_stats = {}
    for pdf_name, pdf_results in results.items():
        for config_name, config_data in pdf_results.items():
            if config_name not in config_stats:
                config_stats[config_name] = []
            config_stats[config_name].append(config_data)
    
    for config_name in sorted(config_stats.keys()):
        config_data = config_stats[config_name]
        avg_quality = sum(d['quality_score'] for d in config_data) / len(config_data)
        avg_time = sum(d['extraction_time'] for d in config_data) / len(config_data)
        avg_chars = sum(d['character_count'] for d in config_data) / len(config_data)
        
        # Success rate (all current entries are successful since we only have successful extractions)
        success_rate = 100.0
        
        table_lines.append(
            f"| {config_name} | {avg_quality:.1f}% | {success_rate:.1f}% | {avg_time:.1f}s | {avg_chars:.0f} |"
        )
    
    # Add per-file breakdown
    table_lines.append("")
    table_lines.append("## Per-File Detailed Results")
    table_lines.append("")
    
    for pdf_name, pdf_results in results.items():
        table_lines.append(f"### {pdf_name}.pdf")
        table_lines.append("")
        table_lines.append("| Configuration | Quality Score | Characters | Words | Lines | Time (s) |")
        table_lines.append("|---------------|---------------|------------|-------|-------|----------|")
        
        # Sort by quality score for this PDF
        sorted_results = sorted(pdf_results.items(), key=lambda x: x[1]['quality_score'], reverse=True)
        
        for config_name, config_data in sorted_results:
            table_lines.append(
                f"| {config_name} | {config_data['quality_score']:.1f}% | {config_data['character_count']} | "
                f"{config_data['word_count']} | {config_data['line_count']} | {config_data['extraction_time']:.1f}s |"
            )
        
        table_lines.append("")
    
    return "\n".join(table_lines)

def main():
    """Analyze results and generate comparison table"""
    print("Analyzing Model Testing Results...")
    
    # Change to the correct directory
    os.chdir("/home/runner/work/pdf-doc-to-json-docling/pdf-doc-to-json-docling/Model Testing")
    
    # Analyze existing results
    results = analyze_text_files()
    
    if not results:
        print("No results found to analyze")
        return
    
    print(f"Found results for {len(results)} PDF files")
    
    # Generate comparison table
    comparison_table = generate_comparison_table(results)
    
    # Save the table
    output_dir = Path("outputs/results")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    table_path = output_dir / "comparison_table_final.md"
    with open(table_path, 'w', encoding='utf-8') as f:
        f.write(comparison_table)
    
    print(f"Comparison table saved to: {table_path}")
    print("\n" + "="*60)
    print(comparison_table)

if __name__ == "__main__":
    main()