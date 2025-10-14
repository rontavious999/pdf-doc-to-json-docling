# Custom Placeholders and Signature Exclusion

This document describes the custom placeholder support and witness/doctor signature exclusion features in the consent converter.

## Overview

The consent converter now supports automatic replacement of common consent form patterns with custom placeholders, and automatically excludes witness and doctor signature fields per Modento schema requirements.

## Custom Placeholders

The following custom placeholders are automatically detected and replaced in consent form HTML content:

### 1. `{{planned_procedure}}`
Replaces patterns like:
- `Planned Procedure: _____`
- `Planned procedure: _____`

**Use case:** When a consent form needs to specify the planned medical/dental procedure.

**Example:**
```
Input:  "Planned Procedure: _____________________"
Output: "Planned Procedure: {{planned_procedure}}"
```

### 2. `{{diagnosis}}`
Replaces patterns like:
- `Diagnosis: _____`
- `diagnosis: _____`

**Use case:** When a consent form needs to specify the patient's diagnosis.

**Example:**
```
Input:  "Diagnosis: _____________________"
Output: "Diagnosis: {{diagnosis}}"
```

### 3. `{{alternative_treatment}}`
Replaces patterns like:
- `Alternative Treatment: _____`
- `alternative treatment: _____`

**Use case:** When a consent form needs to specify alternative treatment options.

**Example:**
```
Input:  "Alternative Treatment: _____________________"
Output: "Alternative Treatment: {{alternative_treatment}}"
```

## Existing Placeholders

The consent converter also supports these existing placeholders:

- `{{provider}}` - Provider/doctor name
- `{{patient_name}}` - Patient name
- `{{patient_dob}}` - Patient date of birth
- `{{tooth_or_site}}` - Tooth number or procedure site

## Pattern Matching Features

All placeholder patterns support:

1. **Case-insensitive matching** - Works with "Planned Procedure", "planned procedure", etc.
2. **Variable underscore lengths** - Matches `___`, `_____`, `_______________`, etc.
3. **Double replacement prevention** - Won't replace text that's already a placeholder
4. **Whitespace flexibility** - Handles variations in spacing

## Witness and Doctor Signature Exclusion

Per Modento schema requirements, the consent converter automatically excludes witness and doctor signature fields from consent forms.

### Excluded Witness Fields

The following patterns are automatically filtered out:

- Witness Signature
- Witness Printed Name / Witness Name
- Witness Date
- Witness Relationship
- Witnessed by
- Any field with "witness:" or "witness" in the context

### Excluded Doctor/Provider Signature Fields

The following patterns are automatically filtered out:

- Doctor Signature
- Dentist Signature
- Physician Signature
- Dr. Signature
- Practitioner Signature
- Provider Signature
- Clinician Signature

### What Gets Preserved

Patient-facing fields are always preserved:
- Patient Signature
- Patient Name
- Date Signed
- Date of Birth
- Other patient information fields

## Implementation Details

### Methods Added

1. **`_is_witness_or_doctor_signature_field(line_lower: str) -> bool`**
   - Identifies if a line contains a witness or doctor signature field
   - Returns `True` if the field should be excluded

2. **`_remove_witness_and_doctor_signatures(content: str) -> str`**
   - Removes witness and doctor signature text from HTML content
   - Processes content line by line to filter out unwanted signatures

### Field Extraction Enhancement

The field extraction process now:
1. Checks each line against witness/doctor signature patterns
2. Skips extraction of matching fields
3. Double-checks field keys to prevent any witness/doctor fields from being included

### HTML Content Filtering

The HTML content generation now:
1. Applies placeholder replacements for all supported patterns
2. Filters out witness and doctor signature text from the final HTML
3. Preserves patient-facing content and fields

## Usage Examples

### Basic Usage

```python
from consent_converter import ConsentToJSONConverter

converter = ConsentToJSONConverter()
result = converter.convert_consent_to_json(
    input_file="consent.docx",
    output_path="consent.json"
)

# Check for placeholders in the generated HTML
spec = result['spec']
form_field = next((f for f in spec if f['key'] == 'form_1'), None)
html_text = form_field['control']['html_text']

# Placeholders will be present as {{placeholder_name}}
if '{{planned_procedure}}' in html_text:
    print("Planned procedure placeholder detected")
```

### Command Line

```bash
python consent_converter.py consent_with_placeholders.docx --output output.json
```

The converter will automatically detect and replace placeholder patterns.

### Running Examples

See the included example scripts:
- `example_custom_placeholders.py` - Demonstrates all placeholder features
- `test_consent_placeholders.py` - Unit tests for placeholder replacement
- `test_integration_placeholders.py` - Integration tests

Run examples:
```bash
python example_custom_placeholders.py
python test_consent_placeholders.py
python test_integration_placeholders.py
```

## Testing

Comprehensive test coverage includes:

1. **Unit Tests** (`test_consent_placeholders.py`):
   - Placeholder replacement with various patterns
   - Witness/doctor signature identification
   - Content filtering
   - Double replacement prevention

2. **Integration Tests** (`test_integration_placeholders.py`):
   - End-to-end extraction with placeholders
   - Field exclusion verification
   - Patient field preservation

All tests can be run to verify functionality:
```bash
python test_consent_placeholders.py
python test_integration_placeholders.py
```

## Schema Compliance

These features ensure compliance with the Modento Forms schema:
- Witness fields are not supported on forms or consents
- Doctor signatures are provider-facing, not patient-facing
- All placeholders follow the `{{placeholder_name}}` format
- HTML content is properly structured and formatted

## Future Enhancements

Potential future additions:
- Additional medical/dental-specific placeholders
- Custom placeholder definitions via configuration
- Support for compound placeholders (e.g., `{{procedure_and_date}}`)
- Placeholder validation and warnings

## Notes

- All placeholder patterns are case-insensitive
- Underscore length variations are automatically handled
- Double replacement is prevented through negative lookahead regex
- Witness/doctor signature exclusion is applied universally to all consent forms
- The feature is backward compatible with existing consent forms
