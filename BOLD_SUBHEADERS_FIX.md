# Bold Subheaders Fix for Consent Forms

## Problem Statement
In the Endo Consent form JSON output, subheaders weren't properly bolded and spaced like they appear in the original DOCX file. The HTML output showed plain text where the DOCX had bold subheaders like "Medications", "Alternative Treatments", "Consent", etc.

## Root Cause
Docling's `export_to_text()` method exports DOCX documents to text/markdown format, but it doesn't consistently preserve bold formatting for all paragraphs. While some bold text gets markdown `**bold**` markers, many bold paragraphs (especially subheaders) are exported as plain text without any formatting indicators.

## Solution
Implemented a dynamic solution that detects bold formatting directly from DOCX file structure using python-docx, without any hardcoding:

### Implementation Steps

1. **Added python-docx Integration** (`ConsentFormFieldExtractor.__init__()`)
   - Conditionally imports python-docx if available
   - Falls back gracefully if not installed

2. **Created Bold Detection Method** (`_detect_bold_lines_from_docx()`)
   - Uses python-docx to read DOCX paragraph formatting
   - Identifies paragraphs where all text runs are bold
   - Returns a dictionary mapping line text to bold status

3. **Enhanced Text Extraction** (`extract_text_from_document()`)
   - Calls bold detection for DOCX files
   - Includes bold line information in pipeline_info for downstream use

4. **Updated Field Extraction** (`extract_consent_form_fields()`)
   - Accepts optional pipeline_info parameter
   - Passes bold line information to HTML generation

5. **Enhanced HTML Generation** (`_create_enhanced_consent_html()`)
   - Detects which lines are bold subheaders based on:
     - Line appears in bold_lines dictionary as bold
     - Line is short (< 100 chars) - typical for headers
     - Line is not a bullet point or field label
   - Wraps bold subheaders with `<strong>` tags
   - Adds extra `<br>` spacing before subheaders (except first line or consecutive headers)

## Results

### Endo Consent Form
- **Before**: 2 bold elements (title only)
- **After**: 7 bold elements (title + 5 subheaders)

### New Bold Subheaders Detected
1. Endodontic (Root Canal) Treatment, Endodontic Surgery, Anesthetics, and Medications
2. Risks More Specific to Endodontic (Root Canal) Treatment
3. Medications
4. Alternative Treatments
5. Consent

### Other Consent Forms Tested
- ✅ Extraction Consent: 4 bold elements detected
- ✅ Denture Consent: 10 bold elements detected
- ✅ Crown & Bridge Consent: Works correctly (has no bold subheaders in original)
- ✅ EndoConsentFINAL122024: Works correctly
- ✅ SureSmileConsent: Works correctly

## Key Features

### ✅ No Hardcoding
- Solution dynamically detects bold formatting from DOCX structure
- Works for any consent form with bold subheaders
- No form-specific patterns or text matching

### ✅ Graceful Fallback
- If python-docx is not available, continues to work with existing functionality
- Only DOCX files use enhanced bold detection
- PDF files continue to work as before

### ✅ Smart Detection
- Only marks appropriate lines as subheaders (short, not bullets, not fields)
- Preserves spacing and structure
- Doesn't interfere with existing markdown cleaning

### ✅ Backward Compatible
- All existing tests pass
- Doesn't break any existing functionality
- PDF processing unchanged

## Technical Details

### Bold Detection Logic
```python
# For each paragraph in DOCX:
runs_with_text = [run for run in para.runs if run.text.strip()]
if runs_with_text:
    is_bold = all(run.bold for run in runs_with_text if run.text.strip())
```

### Subheader Detection Logic
```python
# Line is a bold subheader if:
# 1. It's marked as bold in the DOCX
# 2. It's short (< 100 chars)
# 3. It's not a bullet point
# 4. It doesn't contain underscores (not a field label)
```

### HTML Output
```html
<!-- Before subheader: extra spacing -->
<br>
<strong>Medications</strong>
<br>
<!-- Content follows -->
```

## Files Modified
- `consent_converter.py` - Added bold detection and formatting (88 lines added)

## Dependencies
- python-docx (optional, for enhanced DOCX formatting detection)
- Docling (existing dependency)

## Testing
- ✅ All existing tests pass (`test_consent_placeholders.py`)
- ✅ Tested with 6+ different consent forms
- ✅ Schema validation passes for all forms
- ✅ Visual output verified in HTML preview

## Usage
No changes required - the fix is automatic for all DOCX consent forms:

```bash
python consent_converter.py "docx/Endo Consent .docx" --output output.json
```

## Future Enhancements
If needed, could be extended to:
- Detect italic formatting
- Detect font sizes for header levels
- Support other formatting attributes
- Add configuration for subheader detection rules
