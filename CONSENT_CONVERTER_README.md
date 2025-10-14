# Consent Form Converter

A specialized converter for extracting and converting consent forms from PDF and DOCX documents to Modento Forms JSON format.

## Overview

The Consent Form Converter (`consent_converter.py`) is a standalone, focused tool designed exclusively for processing consent forms. It consolidates all consent-specific logic, rules, formatting, and processing from the main converter into a single, easy-to-use script.

## Features

### Consent-Specific Processing
- **Consent Pattern Recognition**: Identifies consent-specific language patterns (I understand, I acknowledge, I agree, etc.)
- **Title Detection**: Automatically detects form titles from markdown headers (##), bold markdown (**Title**), all-caps, or "Informed Consent for" patterns and uses them as section names
- **Provider Placeholder Substitution**: Automatically replaces doctor names with `{{provider}}` placeholders
- **Signature Section Detection**: Intelligently detects and extracts signature fields
- **Consent Text Formatting**: Proper HTML formatting for consent narrative text

### Field Extraction
- **Universal Field Detection**: Detects common consent form fields:
  - Patient Name (Print)
  - Printed Name
  - Date of Birth
  - Relationship to Patient
  - Authorized Representative
  - Legal Guardian
  - Tooth Number (for dental consents)
  - Procedure Description
  - Alternative Treatment
  - Signature
  - Date Signed

### Modento Schema Compliance
- **Validation**: Ensures output complies with Modento Forms schema
- **Required Elements**: Automatically includes mandatory signature and date fields
- **Field Type Normalization**: Proper input types (name, email, phone, date, etc.)
- **Unique Keys**: Ensures all field keys are globally unique

### Content Cleaning
- **Header/Footer Removal**: Removes practice information (addresses, phone numbers, emails, websites)
- **Practice Info Filtering**: Cleans out office contact details from consent text
- **Whitespace Normalization**: Proper formatting and spacing

## Installation

The consent converter uses the same dependencies as the main converter:

```bash
pip install -r requirements.txt
```

Requirements:
- Python 3.8+
- docling>=2.51.0
- pdfplumber>=0.11.0
- PyPDF2>=3.0.0

## Usage

### Single File Conversion

Convert a single consent form (PDF or DOCX):

```bash
python consent_converter.py path/to/consent.pdf --output consent_output.json
```

Or with auto-generated output filename:

```bash
python consent_converter.py path/to/consent.pdf
# Output will be: path/to/consent.json
```

### Batch Processing

Process multiple consent forms in a directory:

```bash
python consent_converter.py path/to/consent_forms/ --output-dir json_output/
```

Or with auto-generated output directory:

```bash
python consent_converter.py path/to/consent_forms/
# Output will be in: path/to/consent_forms/consent_json_output/
```

### Verbose Mode

Get detailed processing information:

```bash
python consent_converter.py consent.pdf --verbose
```

Verbose output includes:
- Pipeline and backend information
- OCR engine usage details
- Field and section counts
- Validation status and errors

## Output Format

The converter generates JSON compliant with the Modento Forms schema:

```json
[
  {
    "key": "form_1",
    "title": "",
    "section": "Informed Consent for Treatment",
    "optional": false,
    "type": "text",
    "control": {
      "html_text": "<div style=\"text-align:center\"><strong>Informed Consent for Treatment</strong><br>I understand that I am having treatment with Dr. {{provider}}...</div>"
    }
  },
  {
    "key": "printed_name",
    "title": "Printed Name",
    "section": "Signature",
    "optional": false,
    "type": "input",
    "control": {
      "input_type": "name"
    }
  },
  {
    "key": "signature",
    "title": "Signature",
    "section": "Signature",
    "optional": false,
    "type": "signature",
    "control": {}
  },
  {
    "key": "date_signed",
    "title": "Date Signed",
    "section": "Signature",
    "optional": false,
    "type": "date",
    "control": {
      "input_type": "past"
    }
  }
]
```

## Consent-Specific Rules

### 1. Provider Placeholder Substitution
Doctor names are replaced with `{{provider}}` placeholders in consent text:
- `Dr. ____` → `Dr. {{provider}}`
- `authorize Dr. ____` → `authorize Dr. {{provider}}`
- `consent to Dr. ____` → `consent to Dr. {{provider}}`

### 2. Consent Content Detection
The converter identifies consent content using multiple patterns:
- Explicit consent phrases (I understand, I acknowledge, I agree, I consent, I authorize)
- Risk and benefit discussions
- Treatment and procedure descriptions
- Financial responsibility statements

### 3. Signature Requirements
Every consent form must have:
- A signature field (type: signature)
- A date signed field (type: date with input_type: past)

These are automatically added if not detected in the source document.

### 4. Header/Footer Removal
Practice information is automatically removed from consent text:
- Website URLs (www.example.com)
- Email addresses (info@practice.com)
- Phone numbers ((555) 555-5555)
- Physical addresses
- Office contact information

### 5. Field Section Organization
Fields are organized into logical sections:
- **Form**: Main consent text and narrative
- **Signature**: Signature-related fields (name, date, signature)

### 6. Witness Field Handling
Witness fields are excluded per Modento schema requirements for consent forms.

## Processing Pipeline

### For PDF Files
1. Document loading via Docling
2. OCR text extraction (EasyOCR)
3. Header/footer removal
4. Consent section detection
5. Provider placeholder substitution
6. Field extraction
7. Signature field validation
8. Schema validation and normalization

### For DOCX Files
1. Document loading via Docling
2. Native text extraction (no OCR required)
3. Header/footer removal
4. Consent section detection
5. Provider placeholder substitution
6. Field extraction
7. Signature field validation
8. Schema validation and normalization

**Performance**: DOCX processing is approximately 200x faster than PDF processing due to native text extraction.

## Examples

### Example 1: Single Consent Form

```bash
python consent_converter.py consents/informed_consent.pdf --output output/consent.json --verbose
```

Output:
```
[✓] Conversion complete!
[i] Output: output/consent.json
[i] Fields detected: 5
[i] Sections detected: 2
[i] Schema validation: PASSED

[i] Pipeline details:
    - pipeline: PDF
    - backend: DoclingParseDocumentBackend
    - document_format: PDF
    - ocr_used: True
    - ocr_engine: EasyOCR
```

### Example 2: Batch Processing

```bash
python consent_converter.py consents/ --output-dir json_outputs/ --verbose
```

Output:
```
Found 3 consent forms to process: 2 PDF, 1 DOCX

[+] Processing consent1.pdf (PDF) ...
[✓] Wrote JSON: json_outputs/consent1.json
[i] Sections: 2 | Fields: 5
[i] Pipeline/Backend: PDF/DoclingParseDocumentBackend
[i] OCR (EasyOCR): used

[+] Processing consent2.pdf (PDF) ...
[✓] Wrote JSON: json_outputs/consent2.json
[i] Sections: 2 | Fields: 6
[i] Pipeline/Backend: PDF/DoclingParseDocumentBackend
[i] OCR (EasyOCR): used

[+] Processing consent3.docx (DOCX) ...
[✓] Wrote JSON: json_outputs/consent3.json
[i] Sections: 2 | Fields: 4
[i] Pipeline/Backend: DOCX/DoclingParseDocumentBackend
[i] OCR: not required (native text extraction)

[i] Successfully processed: 3/3 consent forms
```

## Architecture

### Key Components

1. **ConsentFormFieldExtractor**: Extracts fields from consent documents
   - Uses Docling for document processing
   - Manages consent-specific patterns
   - Handles provider placeholder substitution

2. **ConsentShapingManager**: Manages consent-specific formatting
   - Detects consent content patterns
   - Formats consent text for display
   - Identifies consent sections

3. **HeaderFooterManager**: Removes practice information
   - Filters practice headers/footers
   - Cleans contact information
   - Preserves form content

4. **ModentoSchemaValidator**: Validates and normalizes output
   - Ensures schema compliance
   - Normalizes field types
   - Validates required fields

5. **ConsentToJSONConverter**: Orchestrates the conversion
   - Manages the conversion pipeline
   - Coordinates component interaction
   - Generates final JSON output

### Design Principles

- **Single Responsibility**: Each component has a focused purpose
- **Consent-Focused**: All logic is specific to consent forms
- **Modento Compliant**: Strict adherence to schema requirements
- **Self-Contained**: No dependencies on other form types
- **Extensible**: Easy to add new consent-specific features

## Differences from Main Converter

The consent converter differs from the main converter in several ways:

1. **Focused Scope**: Only processes consent forms, not patient information forms or other form types
2. **Consent Patterns**: Uses consent-specific detection patterns
3. **Provider Placeholders**: Automatically handles doctor name substitution
4. **Simplified Logic**: Removes complexity related to other form types
5. **Witness Handling**: Excludes witness fields per consent form requirements
6. **Section Organization**: Uses Form and Signature sections specifically

## Troubleshooting

### No Fields Detected
- Ensure the document is actually a consent form
- Check if the document has clear signature sections
- Verify the document contains consent language (I understand, I agree, etc.)

### Provider Placeholders Not Working
- Verify the document has doctor names with underscores or blanks
- Check if the pattern matches: "Dr. ____" or "authorize Dr. ____"

### Validation Errors
- Review the verbose output for specific validation issues
- Ensure all required fields are present in the source document
- Check that field types match expected values

### Performance Issues
- Consider using DOCX format for faster processing (200x speed improvement)
- Ensure sufficient memory for PDF OCR processing
- Check that Docling dependencies are properly installed

## Support

For issues or questions about the consent converter:
1. Check this documentation
2. Review the main repository README
3. Examine the Modento Forms Schema Guide
4. Check the code comments in `consent_converter.py`

## License

This project is licensed under the MIT License - see the LICENSE file for details.
