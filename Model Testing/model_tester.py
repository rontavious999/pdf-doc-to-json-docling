#!/usr/bin/env python3
"""
Model Testing Script for Docling PDF Processing

This script tests different Docling configurations on all PDFs in the pdfs folder
and compares their text extraction performance.
"""

import os
import json
import time
from pathlib import Path
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass
import hashlib

# Docling imports
from docling.document_converter import DocumentConverter, FormatOption
from docling.datamodel.pipeline_options import PdfPipelineOptions, EasyOcrOptions, TesseractOcrOptions, RapidOcrOptions
from docling.datamodel.base_models import InputFormat
from docling.backend.docling_parse_backend import DoclingParseDocumentBackend
from docling.backend.pypdfium2_backend import PyPdfiumDocumentBackend
from docling.pipeline.standard_pdf_pipeline import StandardPdfPipeline


@dataclass
class TestConfiguration:
    """Configuration for a test model"""
    name: str
    description: str
    format_options: Dict[InputFormat, FormatOption]


@dataclass 
class ExtractionResult:
    """Result of text extraction for one configuration"""
    config_name: str
    pdf_file: str
    text_content: str
    extraction_time: float
    character_count: int
    word_count: int
    line_count: int
    success: bool
    error_message: str = ""


class DoclingModelTester:
    """Test different Docling configurations and compare results"""
    
    def __init__(self, pdf_directory: str = "../pdfs", output_directory: str = "./outputs"):
        self.pdf_directory = Path(pdf_directory)
        self.output_directory = Path(output_directory)
        self.output_directory.mkdir(exist_ok=True)
        
        # Create subdirectories for organized output
        (self.output_directory / "text_outputs").mkdir(exist_ok=True)
        (self.output_directory / "results").mkdir(exist_ok=True)
        
        self.configurations = self._create_test_configurations()
        self.results: List[ExtractionResult] = []
    
    def _create_test_configurations(self) -> List[TestConfiguration]:
        """Create different test configurations to compare"""
        configurations = []
        
        # Configuration 1: EasyOCR Standard (baseline)
        config1 = PdfPipelineOptions()
        config1.do_ocr = True
        config1.do_table_structure = True
        config1.images_scale = 1.0
        config1.ocr_options = EasyOcrOptions(
            lang=['en'],
            force_full_page_ocr=False,
            confidence_threshold=0.5
        )
        format_option1 = FormatOption(
            pipeline_options=config1,
            backend=DoclingParseDocumentBackend,
            pipeline_cls=StandardPdfPipeline
        )
        configurations.append(TestConfiguration(
            name="easyocr_standard",
            description="EasyOCR with standard settings",
            format_options={InputFormat.PDF: format_option1}
        ))
        
        # Configuration 2: EasyOCR High Confidence
        config2 = PdfPipelineOptions()
        config2.do_ocr = True
        config2.do_table_structure = True
        config2.images_scale = 1.0
        config2.ocr_options = EasyOcrOptions(
            lang=['en'],
            force_full_page_ocr=False,
            confidence_threshold=0.8
        )
        format_option2 = FormatOption(
            pipeline_options=config2,
            backend=DoclingParseDocumentBackend,
            pipeline_cls=StandardPdfPipeline
        )
        configurations.append(TestConfiguration(
            name="easyocr_high_confidence",
            description="EasyOCR with high confidence threshold (0.8)",
            format_options={InputFormat.PDF: format_option2}
        ))
        
        # Configuration 3: EasyOCR Full Page OCR
        config3 = PdfPipelineOptions()
        config3.do_ocr = True
        config3.do_table_structure = True
        config3.images_scale = 1.0
        config3.ocr_options = EasyOcrOptions(
            lang=['en'],
            force_full_page_ocr=True,
            confidence_threshold=0.5
        )
        format_option3 = FormatOption(
            pipeline_options=config3,
            backend=DoclingParseDocumentBackend,
            pipeline_cls=StandardPdfPipeline
        )
        configurations.append(TestConfiguration(
            name="easyocr_full_page",
            description="EasyOCR with forced full page OCR",
            format_options={InputFormat.PDF: format_option3}
        ))
        
        # Configuration 4: TesseractOCR
        config4 = PdfPipelineOptions()
        config4.do_ocr = True
        config4.do_table_structure = True
        config4.images_scale = 1.0
        config4.ocr_options = TesseractOcrOptions(
            lang=['eng'],
            force_full_page_ocr=False
        )
        format_option4 = FormatOption(
            pipeline_options=config4,
            backend=DoclingParseDocumentBackend,
            pipeline_cls=StandardPdfPipeline
        )
        configurations.append(TestConfiguration(
            name="tesseract_standard",
            description="TesseractOCR with standard settings",
            format_options={InputFormat.PDF: format_option4}
        ))
        
        # Configuration 5: RapidOCR
        config5 = PdfPipelineOptions()
        config5.do_ocr = True
        config5.do_table_structure = True
        config5.images_scale = 1.0
        config5.ocr_options = RapidOcrOptions(
            lang=['english'],
            force_full_page_ocr=False
        )
        format_option5 = FormatOption(
            pipeline_options=config5,
            backend=DoclingParseDocumentBackend,
            pipeline_cls=StandardPdfPipeline
        )
        configurations.append(TestConfiguration(
            name="rapidocr_standard",
            description="RapidOCR with standard settings",
            format_options={InputFormat.PDF: format_option5}
        ))
        
        # Configuration 6: No OCR (PDF parsing only)
        config6 = PdfPipelineOptions()
        config6.do_ocr = False
        config6.do_table_structure = True
        config6.images_scale = 1.0
        format_option6 = FormatOption(
            pipeline_options=config6,
            backend=DoclingParseDocumentBackend,
            pipeline_cls=StandardPdfPipeline
        )
        configurations.append(TestConfiguration(
            name="no_ocr_parsing",
            description="PDF parsing without OCR",
            format_options={InputFormat.PDF: format_option6}
        ))
        
        # Configuration 7: High Resolution
        config7 = PdfPipelineOptions()
        config7.do_ocr = True
        config7.do_table_structure = True
        config7.images_scale = 3.0
        config7.ocr_options = EasyOcrOptions(
            lang=['en'],
            force_full_page_ocr=False,
            confidence_threshold=0.5
        )
        format_option7 = FormatOption(
            pipeline_options=config7,
            backend=DoclingParseDocumentBackend,
            pipeline_cls=StandardPdfPipeline
        )
        configurations.append(TestConfiguration(
            name="easyocr_high_resolution",
            description="EasyOCR with 3x image scaling",
            format_options={InputFormat.PDF: format_option7}
        ))

        # Configuration 8: PyPdfium2 Backend (alternative backend)
        config8 = PdfPipelineOptions()
        config8.do_ocr = False  # PyPdfium2 doesn't do OCR
        config8.do_table_structure = False
        config8.images_scale = 1.0
        format_option8 = FormatOption(
            pipeline_options=config8,
            backend=PyPdfiumDocumentBackend,
            pipeline_cls=StandardPdfPipeline
        )
        configurations.append(TestConfiguration(
            name="pypdfium2_backend",
            description="PyPdfium2 backend (no OCR, fast parsing)",
            format_options={InputFormat.PDF: format_option8}
        ))
        
        return configurations
    
    def extract_text_with_config(self, pdf_path: Path, config: TestConfiguration) -> ExtractionResult:
        """Extract text from PDF using specific configuration"""
        print(f"  Testing {config.name}...", end=" ", flush=True)
        
        start_time = time.time()
        
        try:
            # Create converter with specific configuration
            converter = DocumentConverter(format_options=config.format_options)
            
            # Convert the document
            result = converter.convert(str(pdf_path))
            
            # Extract text content
            text_content = result.document.export_to_text()
            
            extraction_time = time.time() - start_time
            
            # Calculate metrics
            character_count = len(text_content)
            word_count = len(text_content.split())
            line_count = len([line for line in text_content.split('\n') if line.strip()])
            
            print(f"✓ ({extraction_time:.1f}s, {character_count} chars)")
            
            return ExtractionResult(
                config_name=config.name,
                pdf_file=pdf_path.name,
                text_content=text_content,
                extraction_time=extraction_time,
                character_count=character_count,
                word_count=word_count,
                line_count=line_count,
                success=True
            )
            
        except Exception as e:
            extraction_time = time.time() - start_time
            error_msg = str(e)
            
            print(f"✗ Error: {error_msg}")
            
            return ExtractionResult(
                config_name=config.name,
                pdf_file=pdf_path.name,
                text_content="",
                extraction_time=extraction_time,
                character_count=0,
                word_count=0,
                line_count=0,
                success=False,
                error_message=error_msg
            )
    
    def save_text_output(self, result: ExtractionResult) -> None:
        """Save extracted text to file using naming convention"""
        if not result.success or not result.text_content.strip():
            return
            
        # Create filename following the convention {file-name}_{model_name}.txt
        pdf_name = Path(result.pdf_file).stem
        output_filename = f"{pdf_name}_{result.config_name}.txt"
        output_path = self.output_directory / "text_outputs" / output_filename
        
        # Write text content
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(f"# Text Extraction Result\n")
            f.write(f"PDF File: {result.pdf_file}\n")
            f.write(f"Model/Configuration: {result.config_name}\n")
            f.write(f"Extraction Time: {result.extraction_time:.2f} seconds\n")
            f.write(f"Character Count: {result.character_count}\n")
            f.write(f"Word Count: {result.word_count}\n")
            f.write(f"Line Count: {result.line_count}\n")
            f.write(f"\n{'='*50}\n")
            f.write(f"EXTRACTED TEXT:\n")
            f.write(f"{'='*50}\n\n")
            f.write(result.text_content)
    
    def run_tests(self) -> None:
        """Run all configurations on all PDFs"""
        # Find all PDF files
        pdf_files = list(self.pdf_directory.glob("*.pdf"))
        
        if not pdf_files:
            print(f"No PDF files found in {self.pdf_directory}")
            return
            
        # Take only first 5 PDFs as requested
        pdf_files = pdf_files[:5]
        
        print(f"Found {len(pdf_files)} PDF files to test:")
        for pdf in pdf_files:
            print(f"  - {pdf.name}")
        
        print(f"\nTesting {len(self.configurations)} configurations:")
        for config in self.configurations:
            print(f"  - {config.name}: {config.description}")
        
        print(f"\nStarting tests...")
        print("="*60)
        
        # Test each PDF with each configuration
        for pdf_path in pdf_files:
            print(f"\nProcessing {pdf_path.name}:")
            
            for config in self.configurations:
                result = self.extract_text_with_config(pdf_path, config)
                self.results.append(result)
                
                # Save text output
                self.save_text_output(result)
        
        print(f"\n{'='*60}")
        print("All tests completed!")
    
    def calculate_extraction_quality(self, text: str) -> float:
        """Calculate a simple quality score for extracted text"""
        if not text or not text.strip():
            return 0.0
        
        # Basic quality metrics
        char_count = len(text)
        word_count = len(text.split())
        line_count = len([line for line in text.split('\n') if line.strip()])
        
        # Check for common indicators of good extraction
        has_proper_spacing = text.count(' ') > char_count * 0.1
        has_line_breaks = line_count > 1
        has_reasonable_word_length = word_count > 0 and char_count / word_count < 20
        
        # Simple scoring (can be improved with more sophisticated metrics)
        base_score = min(100, char_count / 10)  # More characters generally better
        
        if has_proper_spacing:
            base_score *= 1.2
        if has_line_breaks:
            base_score *= 1.1
        if has_reasonable_word_length:
            base_score *= 1.1
            
        return min(100.0, base_score)
    
    def generate_comparison_table(self) -> str:
        """Generate comparison table showing best performing models"""
        if not self.results:
            return "No results to compare"
        
        # Group results by PDF file
        by_pdf = {}
        for result in self.results:
            if result.pdf_file not in by_pdf:
                by_pdf[result.pdf_file] = []
            by_pdf[result.pdf_file].append(result)
        
        # Create comparison table
        table_lines = []
        table_lines.append("# Model Testing Comparison Results")
        table_lines.append("")
        table_lines.append("| PDF File | Best Model | Extraction % | Second Best | Extraction % |")
        table_lines.append("|----------|------------|--------------|-------------|--------------|")
        
        for pdf_file, pdf_results in by_pdf.items():
            # Calculate quality scores for each result
            scored_results = []
            for result in pdf_results:
                if result.success:
                    quality = self.calculate_extraction_quality(result.text_content)
                    scored_results.append((result, quality))
            
            if not scored_results:
                table_lines.append(f"| {pdf_file} | No successful extractions | 0% | - | - |")
                continue
            
            # Sort by quality score (descending)
            scored_results.sort(key=lambda x: x[1], reverse=True)
            
            # Get best and second best
            best_result, best_score = scored_results[0]
            second_result, second_score = scored_results[1] if len(scored_results) > 1 else (None, 0)
            
            second_model = second_result.config_name if second_result else "N/A"
            second_pct = f"{second_score:.1f}%" if second_result else "N/A"
            
            table_lines.append(
                f"| {pdf_file} | {best_result.config_name} | {best_score:.1f}% | {second_model} | {second_pct} |"
            )
        
        # Add detailed statistics
        table_lines.append("")
        table_lines.append("## Detailed Statistics")
        table_lines.append("")
        
        # Configuration performance summary
        config_performance = {}
        for result in self.results:
            if result.config_name not in config_performance:
                config_performance[result.config_name] = []
            if result.success:
                quality = self.calculate_extraction_quality(result.text_content)
                config_performance[result.config_name].append(quality)
        
        table_lines.append("### Average Performance by Configuration")
        table_lines.append("")
        table_lines.append("| Configuration | Average Score | Success Rate | Avg Time (s) |")
        table_lines.append("|---------------|---------------|--------------|--------------|")
        
        for config_name in sorted(config_performance.keys()):
            config_results = [r for r in self.results if r.config_name == config_name]
            successful_results = [r for r in config_results if r.success]
            
            if config_performance[config_name]:
                avg_score = sum(config_performance[config_name]) / len(config_performance[config_name])
            else:
                avg_score = 0
            
            success_rate = len(successful_results) / len(config_results) * 100 if config_results else 0
            avg_time = sum(r.extraction_time for r in successful_results) / len(successful_results) if successful_results else 0
            
            table_lines.append(f"| {config_name} | {avg_score:.1f}% | {success_rate:.1f}% | {avg_time:.1f}s |")
        
        return "\n".join(table_lines)
    
    def save_results(self) -> None:
        """Save detailed results and comparison table"""
        # Save raw results as JSON
        results_data = []
        for result in self.results:
            results_data.append({
                'config_name': result.config_name,
                'pdf_file': result.pdf_file,
                'extraction_time': result.extraction_time,
                'character_count': result.character_count,
                'word_count': result.word_count,
                'line_count': result.line_count,
                'success': result.success,
                'error_message': result.error_message,
                'extraction_quality': self.calculate_extraction_quality(result.text_content) if result.success else 0
            })
        
        results_path = self.output_directory / "results" / "detailed_results.json"
        with open(results_path, 'w', encoding='utf-8') as f:
            json.dump(results_data, f, indent=2)
        
        # Save comparison table
        comparison_table = self.generate_comparison_table()
        table_path = self.output_directory / "results" / "comparison_table.md"
        with open(table_path, 'w', encoding='utf-8') as f:
            f.write(comparison_table)
        
        print(f"\nResults saved:")
        print(f"  - Detailed results: {results_path}")
        print(f"  - Comparison table: {table_path}")
        print(f"  - Text outputs: {self.output_directory / 'text_outputs'}")


def main():
    """Main function to run model testing"""
    print("Docling Model Testing Framework")
    print("="*50)
    
    # Create tester instance
    tester = DoclingModelTester()
    
    # Run all tests
    tester.run_tests()
    
    # Save results and generate comparison
    tester.save_results()
    
    # Print summary
    print(f"\nTest Summary:")
    print(f"  - Total test runs: {len(tester.results)}")
    print(f"  - Successful extractions: {sum(1 for r in tester.results if r.success)}")
    print(f"  - Failed extractions: {sum(1 for r in tester.results if not r.success)}")
    
    # Display comparison table
    print("\n" + tester.generate_comparison_table())


if __name__ == "__main__":
    main()