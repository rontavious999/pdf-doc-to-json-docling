# Model Testing Comparison Results

## Summary

This table shows the best performing Docling configurations for each PDF file.

| PDF File | Best Model | Extraction % | Second Best | Extraction % |
|----------|------------|--------------|-------------|--------------|
| npf1.pdf | easyocr_standard | 100.0% | easyocr_high_confidence | 100.0% |
| Chicago-Dental-Solutions_Form.pdf | pypdfium2_backend | 100.0% | no_ocr_parsing | 100.0% |
| tooth20removal20consent20form.pdf | easyocr_high_resolution | 100.0% | easyocr_full_page | 100.0% |
| CFGingivectomy.pdf | pypdfium2_backend | 100.0% | easyocr_full_page | 100.0% |
| consent_crown_bridge_prosthetics.pdf | easyocr_full_page | 100.0% | easyocr_high_confidence | 100.0% |

## Detailed Statistics

### Configuration Performance Summary

| Configuration | Avg Quality Score | Success Rate | Avg Time (s) | Avg Characters |
|---------------|-------------------|--------------|--------------|----------------|
| easyocr_full_page | 100.0% | 100.0% | 87.7s | 3628 |
| easyocr_high_confidence | 100.0% | 100.0% | 12.6s | 5364 |
| easyocr_high_resolution | 100.0% | 100.0% | 13.9s | 4159 |
| easyocr_standard | 100.0% | 100.0% | 12.8s | 5364 |
| no_ocr_parsing | 100.0% | 100.0% | 6.5s | 4159 |
| pypdfium2_backend | 100.0% | 100.0% | 3.5s | 4130 |

## Per-File Detailed Results

### npf1.pdf

| Configuration | Quality Score | Characters | Words | Lines | Time (s) |
|---------------|---------------|------------|-------|-------|----------|
| easyocr_standard | 100.0% | 10183 | 1031 | 316 | 8.2s |
| easyocr_high_confidence | 100.0% | 10183 | 1031 | 316 | 8.4s |

### Chicago-Dental-Solutions_Form.pdf

| Configuration | Quality Score | Characters | Words | Lines | Time (s) |
|---------------|---------------|------------|-------|-------|----------|
| pypdfium2_backend | 100.0% | 4601 | 633 | 193 | 4.7s |
| no_ocr_parsing | 100.0% | 4720 | 732 | 214 | 13.3s |
| easyocr_high_confidence | 100.0% | 4720 | 732 | 214 | 36.8s |
| easyocr_full_page | 100.0% | 3771 | 534 | 188 | 118.8s |
| easyocr_standard | 100.0% | 4720 | 732 | 214 | 37.4s |
| easyocr_high_resolution | 100.0% | 4720 | 732 | 214 | 37.7s |

### tooth20removal20consent20form.pdf

| Configuration | Quality Score | Characters | Words | Lines | Time (s) |
|---------------|---------------|------------|-------|-------|----------|
| easyocr_high_resolution | 100.0% | 1753 | 272 | 15 | 5.0s |
| easyocr_full_page | 100.0% | 1677 | 264 | 16 | 50.9s |
| pypdfium2_backend | 100.0% | 1762 | 277 | 15 | 2.4s |
| easyocr_standard | 100.0% | 1753 | 272 | 15 | 4.7s |
| easyocr_high_confidence | 100.0% | 1753 | 272 | 15 | 4.8s |
| no_ocr_parsing | 100.0% | 1753 | 272 | 15 | 3.4s |

### CFGingivectomy.pdf

| Configuration | Quality Score | Characters | Words | Lines | Time (s) |
|---------------|---------------|------------|-------|-------|----------|
| pypdfium2_backend | 100.0% | 4559 | 731 | 33 | 2.5s |
| easyocr_full_page | 100.0% | 4118 | 657 | 30 | 67.0s |
| easyocr_standard | 100.0% | 4574 | 729 | 31 | 5.1s |
| easyocr_high_confidence | 100.0% | 4574 | 729 | 31 | 5.1s |
| no_ocr_parsing | 100.0% | 4574 | 729 | 31 | 3.5s |
| easyocr_high_resolution | 100.0% | 4574 | 729 | 31 | 5.2s |

### consent_crown_bridge_prosthetics.pdf

| Configuration | Quality Score | Characters | Words | Lines | Time (s) |
|---------------|---------------|------------|-------|-------|----------|
| easyocr_full_page | 100.0% | 4948 | 770 | 28 | 114.1s |
| easyocr_high_confidence | 100.0% | 5589 | 837 | 28 | 7.7s |
| no_ocr_parsing | 100.0% | 5589 | 837 | 28 | 6.1s |
| easyocr_standard | 100.0% | 5589 | 837 | 28 | 8.4s |
| easyocr_high_resolution | 100.0% | 5589 | 837 | 28 | 7.9s |
| pypdfium2_backend | 100.0% | 5598 | 844 | 32 | 4.5s |
