# PDF to Modento Forms JSON Converter

This project provides tools to extract form fields from PDF documents and convert them to JSON format compliant with the Modento Forms schema specification.

## Features

- **PDF Form Field Extraction**: Automatically detects and extracts form fields from PDF documents
- **Modento Schema Compliance**: Generates JSON that validates against the Modento Forms schema
- **Multiple Field Types**: Supports input, radio, dropdown, date, signature, and other field types
- **Batch Processing**: Process multiple PDFs in a directory at once
- **Field Type Detection**: Intelligently detects field types (email, phone, date, etc.)
- **Section Organization**: Groups fields into logical sections
- **Validation**: Built-in validation and normalization of output JSON

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

## Supported Field Types

The converter automatically detects and maps the following field types:

- **Input Fields**: name, email, phone, number, ssn, zip, initials
- **Date Fields**: birth dates, current dates, etc.
- **Radio Buttons**: yes/no questions, multiple choice options
- **States**: US state selection
- **Signature**: signature fields
- **Text**: informational text blocks

## Schema Compliance

The generated JSON follows the Modento Forms schema specification:

- Unique field keys throughout the form
- Proper field type definitions
- Required control structures for each field type
- Automatic signature field inclusion
- Section-based organization

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
├── pdf_to_json_converter.py    # Main conversion script
├── batch_converter.py          # Batch processing script
├── requirements.txt            # Python dependencies
├── pdfs/                       # Sample PDF files
├── references/                 # Reference JSON files
└── README.md                   # This file
```

### Key Components

- **PDFFormFieldExtractor**: Extracts form fields from PDF text
- **ModentoSchemaValidator**: Validates and normalizes JSON output
- **FieldInfo**: Data structure for field information
- **PDFToJSONConverter**: Main conversion orchestrator

## Limitations

- Text extraction quality depends on PDF structure and formatting
- Complex form layouts may require manual refinement
- OCR is not currently implemented for scanned PDFs
- Field detection relies on text patterns and may miss unusual formats

## Future Enhancements

- Integration with Docling for advanced PDF processing (when network access allows model downloads)
- OCR support for scanned documents
- Advanced table extraction
- Custom field mapping rules
- Interactive field validation and correction

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.