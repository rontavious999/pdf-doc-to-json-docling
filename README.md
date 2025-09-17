# PDF and DOCX to Modento Forms JSON Converter (Enhanced with Docling)

This project provides advanced tools to extract form fields from PDF and DOCX documents and convert them to JSON format compliant with the Modento Forms schema specification, powered by IBM's Docling for superior accuracy.

## Features

- **Multi-Format Support**: Process both PDF and DOCX documents with optimal performance for each format
- **Advanced PDF Processing**: Powered by Docling with cutting-edge AI models for superior text and form extraction
- **Lightning-Fast DOCX Processing**: Native text extraction from Word documents (200x faster than PDF OCR)
- **OCR Integration**: Built-in EasyOCR support for scanned documents and image-based forms
- **Table Structure Detection**: Advanced table parsing capabilities
- **Multiple Field Types**: Supports input, radio, dropdown, date, signature, and other field types
- **Intelligent Field Detection**: Enhanced pattern recognition for accurate field identification
- **Modento Schema Compliance**: Generates JSON that validates against the Modento Forms schema
- **Batch Processing**: Process multiple PDFs and DOCX files efficiently with detailed progress reporting
- **Section Organization**: Groups fields into logical sections automatically
- **Validation**: Built-in validation and normalization of output JSON
- **Detailed Pipeline Reporting**: Comprehensive information about processing backend and models used

## 🚀 DOCX Support - New Performance Champion

**Transform your workflow with DOCX processing:**

✅ **200x Faster Processing**: DOCX files complete in ~0.05 seconds vs ~11 seconds for PDFs  
✅ **Superior Text Quality**: Native text extraction eliminates OCR artifacts  
✅ **Zero Learning Curve**: Same commands, same output format  
✅ **Mixed Batch Processing**: Handle PDF and DOCX files together seamlessly  

**Performance Comparison:**
- 📄 **PDF Processing**: 11.9s (with OCR)
- 📝 **DOCX Processing**: 0.06s (native extraction)
- ⚡ **Speed Boost**: 200x performance improvement

Perfect for forms originally created in Word that need rapid processing!

## Enhanced Output Format

The converter now provides detailed processing information for each conversion, with format detection:

```
[+] Processing filename.pdf (PDF) ...
[✓] Wrote JSON: output_folder/filename.json
[i] Sections: 3 | Fields: 97
[i] Pipeline/Model/Backend used: StandardPdfPipeline/DoclingParseDocumentBackend
[x] OCR (EasyOCR): used

[+] Processing filename.docx (DOCX) ...
[✓] Wrote JSON: output_folder/filename.json
[i] Sections: 2 | Fields: 17
[i] Pipeline/Model/Backend used: SimplePipeline/DoclingParseDocumentBackend
[i] OCR: not required (native text extraction)
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

### Convert Single PDF or DOCX

```bash
python modular_converter.py <path-to-file> [--output <output.json>] [--verbose]
```

Examples:
```bash
# Process a PDF document
python modular_converter.py pdfs/npf.pdf --output npf_form.json --verbose

# Process a DOCX document (much faster!)
python modular_converter.py forms/patient_form.docx --output patient_form.json --verbose
```

### Batch Convert Multiple Files

```bash
python modular_converter.py <directory-with-files> [--output <output-directory>] [--verbose]
```

Examples:
```bash
# Process mixed directory with PDFs and DOCX files
python modular_converter.py documents --output-dir converted_forms --verbose

# Process specific PDFs directory
python modular_converter.py pdfs --output-dir json_output --verbose
```

**Batch Processing Output:**
```
Found 5 files to process: 3 PDF, 2 DOCX

[+] Processing form1.pdf (PDF) ...
[+] Processing form2.docx (DOCX) ...
[+] Processing form3.pdf (PDF) ...
```

### Demo

Run the demo to see the enhanced capabilities:
```bash
python demo.py
```

## Advanced Processing Capabilities

### Multi-Format Document Support

The converter now supports both PDF and DOCX formats with optimized processing for each:

**PDF Processing:**
- **StandardPdfPipeline**: Advanced document structure analysis
- **EasyOCR**: Optical character recognition for scanned documents
- **Complex Layout Handling**: AI-powered analysis of complex form layouts

**DOCX Processing:**
- **SimplePipeline**: Direct text extraction from Word documents
- **Native Text Access**: No OCR required, significantly faster processing
- **200x Performance Improvement**: DOCX files process in ~0.05s vs ~11s for PDFs

### Docling Integration

The converter uses IBM's Docling for advanced document processing:

- **DocumentFormFieldExtractor**: Unified processing for PDF and DOCX formats
- **DoclingParseDocumentBackend**: AI-powered content extraction  
- **Automatic Format Detection**: Optimal pipeline selection based on file type
- **Table Structure Detection**: Automatic table parsing and field extraction
- **Enhanced Layout Analysis**: Superior handling of complex form layouts

### Processing Pipeline

1. **Format Detection**: Automatic identification of PDF vs DOCX format
2. **Document Analysis**: Advanced structure detection using Docling's AI models
3. **Text Extraction**: 
   - PDF: OCR processing for scanned or image-based content
   - DOCX: Native text extraction (no OCR required)
4. **Field Extraction**: Intelligent pattern matching and contextual analysis
5. **Schema Validation**: Modento Forms compliance checking
6. **JSON Generation**: Optimized output with unique field keys and proper structure

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

The repository includes sample documents and their corresponding reference JSON files:

- `pdfs/` - Sample dental form PDFs
- `test_docs/` - Sample DOCX documents
- `references/Matching JSON References/` - Reference JSON outputs
- `Modento_Forms_Schema_Guide (1).txt` - Complete schema specification
- `starter_form_spec (1).json` - Example starter form

## Development

### Modular Architecture

The converter has been redesigned with a modular architecture for better maintainability and extensibility:

```
pdf-doc-to-json-docling/
├── modular_converter.py         # Main modular conversion script
├── pdf_to_json_converter.py     # Original conversion script
├── pdf_to_json_converter_backup.py # Legacy components
├── demo.py                      # Demonstration script
├── document_processing/         # Document text extraction and classification
│   ├── text_extractor.py       # Document text extraction using Docling
│   └── form_classifier.py      # Form type detection and classification
├── field_detection/             # Field detection modules
│   ├── field_detector.py       # Core field detection logic
│   ├── input_detector.py       # Input field detection
│   └── radio_detector.py       # Radio button detection
├── content_processing/          # Content processing modules
│   └── section_manager.py      # Section and content management
├── field_validation/            # Field validation and normalization
│   └── field_normalizer.py     # Field data normalization
├── requirements.txt             # Python dependencies (including Docling)
├── pdfs/                        # Sample PDF files
├── references/                  # Reference JSON files
├── Model Testing/               # OCR model testing framework
└── README.md                    # This file
```

### Modular Components

The modular architecture provides clear separation of concerns:

#### Document Processing
- **DocumentTextExtractor**: Handles text extraction from PDF and DOCX using Docling
- **FormClassifier**: Detects and classifies form types for optimized processing

#### Field Detection
- **FieldDetector**: Core field detection and pattern matching
- **InputDetector**: Specialized detection for input fields (name, email, phone, etc.)
- **RadioDetector**: Detection and processing of radio buttons and checkboxes

#### Content Processing
- **SectionManager**: Manages form sections and content organization

#### Field Validation
- **FieldNormalizer**: Normalizes and validates field data according to Modento schema

### Benefits of Modular Design

The modular architecture provides several advantages:

✅ **Maintainability**: Each module has a single responsibility, making code easier to understand and maintain  
✅ **Extensibility**: New field types and detection methods can be added by extending specific modules  
✅ **Testability**: Individual modules can be tested in isolation with focused unit tests  
✅ **Reusability**: Modules can be reused across different processing pipelines  
✅ **Scalability**: Processing can be optimized by replacing or upgrading individual modules  
✅ **Compatibility**: Legacy functionality is preserved through the backup converter integration  

### Key Components

- **ModularDocumentFormFieldExtractor**: Integrates all modules for comprehensive field extraction
- **ModularDocumentToJSONConverter**: Main orchestrator using modular components
- **ModentoSchemaValidator**: Validates and normalizes JSON output
- **FieldInfo**: Data structure for field information

## Performance & Accuracy

With multi-format support and Docling integration, the converter now provides:

### PDF Processing:
- **Superior Text Extraction**: AI-powered layout analysis
- **OCR Capabilities**: Built-in support for scanned documents
- **Enhanced Field Detection**: More accurate pattern recognition
- **Better Table Handling**: Advanced table structure detection
- **Improved Form Layout Analysis**: Better understanding of complex forms

### DOCX Processing:
- **Lightning-Fast Performance**: 200x faster than PDF processing
- **Native Text Extraction**: Direct access to Word document content
- **No OCR Required**: Eliminates scanning artifacts and errors
- **Superior Text Quality**: Perfect text preservation from source documents
- **Instant Processing**: Typical forms process in under 0.1 seconds

### Performance Comparison:
- **PDF Form (npf.pdf)**: ~11.9 seconds (with OCR)
- **DOCX Form (equivalent)**: ~0.06 seconds (native extraction)
- **Speed Improvement**: 200x faster for DOCX format

## Processing Models

The converter uses different processing models optimized for each document format:

### PDF Documents:
- **Pipeline**: StandardPdfPipeline (Docling's primary PDF processing pipeline)
- **Backend**: DoclingParseDocumentBackend (AI-powered document parser)
- **OCR Engine**: EasyOCR (for text recognition in images and scanned documents)
- **Table Detection**: Built-in table structure analysis
- **Layout Analysis**: Advanced document structure understanding

### DOCX Documents:
- **Pipeline**: SimplePipeline (optimized for native text extraction)
- **Backend**: DoclingParseDocumentBackend (direct content access)
- **Text Extraction**: Native Word document API access
- **No OCR Required**: Direct text and formatting preservation
- **Faster Processing**: Streamlined pipeline for immediate results

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.