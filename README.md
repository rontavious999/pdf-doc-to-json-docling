# PDF to Modento Forms JSON Converter (Enhanced with Docling)

This project provides advanced tools to extract form fields from PDF documents and convert them to JSON format compliant with the Modento Forms schema specification, powered by IBM's Docling for superior accuracy.

## Features

- **Advanced PDF Processing**: Powered by Docling with cutting-edge AI models for superior text and form extraction
- **OCR Integration**: Built-in EasyOCR support for scanned documents and image-based forms
- **Table Structure Detection**: Advanced table parsing capabilities
- **Multiple Field Types**: Supports input, radio, dropdown, date, signature, and other field types
- **Intelligent Field Detection**: Enhanced pattern recognition for accurate field identification
- **Modento Schema Compliance**: Generates JSON that validates against the Modento Forms schema
- **Batch Processing**: Process multiple PDFs efficiently with detailed progress reporting
- **Section Organization**: Groups fields into logical sections automatically
- **Validation**: Built-in validation and normalization of output JSON
- **Detailed Pipeline Reporting**: Comprehensive information about processing backend and models used

## Enhanced Output Format

The converter now provides detailed processing information for each conversion:

```
[+] Processing filename.pdf ...
[✓] Wrote JSON: output_folder/filename.json
[i] Sections: 3 | Fields: 97
[i] Pipeline/Model/Backend used: StandardPdfPipeline/DoclingParseDocumentBackend
[x] OCR (EasyOCR): used
```

## Installation

1. Clone this repository:
```bash
git clone <repository-url>
cd pdf-doc-to-json-docling
```

2. Install required dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Convert Single PDF

```bash
python pdf_to_json_converter.py <path-to-pdf> [--output <output.json>] [--verbose]
```

Example:
```bash
python pdf_to_json_converter.py pdfs/npf.pdf --output npf_form.json --verbose
```

### Batch Convert Multiple PDFs

```bash
python batch_converter.py <directory-with-pdfs> [--output-dir <output-directory>] [--verbose]
```

Example:
```bash
python batch_converter.py pdfs --output-dir converted_forms --verbose
```

### Demo

Run the demo to see the enhanced capabilities:
```bash
python demo.py
```

## Advanced Processing Capabilities

### Docling Integration

The converter now uses IBM's Docling for advanced PDF processing:

- **StandardPdfPipeline**: Advanced document structure analysis
- **DoclingParseDocumentBackend**: AI-powered content extraction  
- **EasyOCR**: Optical character recognition for scanned documents
- **Table Structure Detection**: Automatic table parsing and field extraction
- **Enhanced Layout Analysis**: Superior handling of complex form layouts

### Processing Pipeline

1. **Document Analysis**: Advanced structure detection using Docling's AI models
2. **OCR Processing**: Automatic text recognition for scanned or image-based content
3. **Field Extraction**: Intelligent pattern matching and contextual analysis
4. **Schema Validation**: Modento Forms compliance checking
5. **JSON Generation**: Optimized output with unique field keys and proper structure

## Supported Field Types

The converter automatically detects and maps the following field types:

- **Input Fields**: name, email, phone, number, ssn, zip, initials
- **Date Fields**: birth dates, current dates, etc. (with past/future constraints)
- **Radio Buttons**: yes/no questions, multiple choice options
- **States**: US state selection fields  
- **Signature**: signature fields
- **Checkbox Groups**: Multi-select options

## Schema Compliance

The generated JSON follows the Modento Forms schema specification:

- Unique field keys throughout the form
- Proper field type definitions and control structures
- Automatic signature field inclusion
- Section-based organization
- Input type validation and normalization

## Output Format

Each generated JSON contains an array of field objects with the following structure:

```json
{
  "key": "unique_field_key",
  "title": "Human Readable Field Name", 
  "section": "Form Section",
  "optional": true,
  "type": "input|radio|date|signature|etc",
  "control": {
    "input_type": "name|email|phone|etc",
    "options": [...],
    "hint": null
  }
}
```

## Example Files

The repository includes sample PDFs and their corresponding reference JSON files:

- `pdfs/` - Sample dental form PDFs
- `references/Matching JSON References/` - Reference JSON outputs
- `Modento_Forms_Schema_Guide (1).txt` - Complete schema specification
- `starter_form_spec (1).json` - Example starter form

## Development

### Project Structure

```
pdf-doc-to-json-docling/
├── pdf_to_json_converter.py    # Main conversion script (Docling-enhanced)
├── batch_converter.py          # Batch processing script
├── demo.py                     # Demonstration script
├── validate_output.py          # Output validation script
├── requirements.txt            # Python dependencies (including Docling)
├── pdfs/                       # Sample PDF files
├── references/                 # Reference JSON files
└── README.md                   # This file
```

### Key Components

- **PDFFormFieldExtractor**: Advanced field extraction using Docling
- **ModentoSchemaValidator**: Validates and normalizes JSON output
- **FieldInfo**: Data structure for field information
- **PDFToJSONConverter**: Main conversion orchestrator with pipeline reporting

## Performance & Accuracy

With Docling integration, the converter now provides:

- **Superior Text Extraction**: AI-powered layout analysis
- **OCR Capabilities**: Built-in support for scanned documents
- **Enhanced Field Detection**: More accurate pattern recognition
- **Better Table Handling**: Advanced table structure detection
- **Improved Form Layout Analysis**: Better understanding of complex forms

## Processing Models

The converter uses the following advanced models:

- **Pipeline**: StandardPdfPipeline (Docling's primary PDF processing pipeline)
- **Backend**: DoclingParseDocumentBackend (AI-powered document parser)
- **OCR Engine**: EasyOCR (for text recognition in images and scanned documents)
- **Table Detection**: Built-in table structure analysis
- **Layout Analysis**: Advanced document structure understanding

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.