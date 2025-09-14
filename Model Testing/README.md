# Model Testing Framework

This folder contains the model testing framework for comparing different Docling configurations and their text extraction performance on PDF documents. 

**Note**: The main converter now supports both PDF and DOCX formats. For DOCX files, native text extraction provides superior performance (200x faster) without requiring OCR model testing.

## Purpose

The goal is to test all PDFs in the `pdfs` folder using at least 5 different Docling models/options and compare their text extraction quality to determine which configuration works best for each document.

## Files

- `model_tester.py` - Main testing script that runs different Docling configurations
- `outputs/` - Directory containing test results (created when tests are run)
  - `text_outputs/` - Individual text extraction files using naming convention `{file-name}_{model_name}.txt`
  - `results/` - Comparison tables and detailed JSON results

## Test Configurations

The framework tests 7 different Docling configurations:

1. **easyocr_standard** - EasyOCR with standard settings (baseline)
2. **easyocr_high_confidence** - EasyOCR with high confidence threshold (0.8)
3. **easyocr_full_page** - EasyOCR with forced full page OCR
4. **tesseract_standard** - TesseractOCR with standard settings
5. **rapidocr_standard** - RapidOCR with standard settings
6. **no_ocr_parsing** - PDF parsing without OCR
7. **easyocr_high_resolution** - EasyOCR with 3x image scaling

## Usage

### Running the Tests

```bash
cd "Model Testing"
python model_tester.py
```

The script will:
1. Test the first 5 PDFs from the `../pdfs` directory
2. Run each PDF through all 7 configurations
3. Extract text and save it with the naming convention `{file-name}_{model_name}.txt`
4. Generate comparison tables showing which model performed best for each file

### Output Files

After running the tests, you'll find:

- **Text outputs**: `outputs/text_outputs/{pdf_name}_{config_name}.txt`
- **Comparison table**: `outputs/results/comparison_table.md`
- **Detailed results**: `outputs/results/detailed_results.json`

### Results Format

The comparison table shows:
- Which model/configuration achieved the best extraction percentage for each PDF
- Which model came in second place
- Detailed statistics for all configurations including average performance, success rates, and processing times

## Quality Metrics

The framework evaluates extraction quality based on:
- Character count (more comprehensive extraction)
- Proper word spacing
- Line breaks preservation
- Reasonable word-to-character ratios

## Dependencies

- Python 3.8+
- docling>=2.51.0
- All dependencies from the main project's requirements.txt

## Example Output

```
| PDF File | Best Model | Extraction % | Second Best | Extraction % |
|----------|------------|--------------|-------------|--------------|
| npf.pdf | easyocr_full_page | 95.2% | easyocr_standard | 89.1% |
| consent_crown_bridge_prosthetics.pdf | tesseract_standard | 92.8% | easyocr_high_confidence | 87.3% |
```

This helps identify which Docling configuration works best for different types of PDF documents.