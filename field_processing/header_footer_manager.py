"""
Header/Footer Processing Manager

Centralized handling of header and footer removal to eliminate duplication
between legacy and modular components.
"""

import re
from typing import List


class HeaderFooterManager:
    """Manages universal header/footer removal for form documents"""
    
    # Practice information patterns that should be removed
    PRACTICE_PATTERNS = [
        # Contact information
        r'.*\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b.*',  # Phone numbers
        r'.*@.*\.(com|org|net|edu).*',  # Email addresses
        r'.*www\..*\.com.*',  # Websites
        
        # Address patterns
        r'.*\b\d+\s+[A-Za-z\s]+(?:street|st|avenue|ave|road|rd|drive|dr|lane|ln|blvd|boulevard)\b.*',
        r'.*\b[A-Za-z\s]+,\s*[A-Z]{2}\s+\d{5}.*',  # City, State ZIP
        
        # Practice types and names
        r'.*\b(dental|dentistry|orthodontics|endodontics|periodontics|oral\s+surgery)\b.*',
        r'.*\b(clinic|center|associates|group|practice|office|care|solutions)\b.*',
        
        # Header/footer formatting
        r'.*•.*•.*•.*',  # Multiple bullet separators (common in headers/footers)
        
        # Practice name patterns (common practice naming conventions)
        r'.*[Ss]mile.*[Dd]ental.*',
        r'.*[Kk]ingery.*[Dd]ental.*',
        r'.*[Dd]arien.*IL.*',
        
        # Generic patterns for header/footer content
        r'^[^a-zA-Z]*$',  # Lines with only symbols/numbers
        r'^\\s*•\\s*$',     # Lines with just bullet points
        
        # Footer information
        r'.*page\\s+\\d+.*',
        r'.*©.*\\d{4}.*',
        r'.*all\\s+rights\\s+reserved.*',
        
        # Form metadata
        r'.*form\\s*(id|number|version).*',
        r'.*revised.*\\d{4}.*',
    ]
    
    def __init__(self):
        """Initialize the header/footer manager"""
        self.compiled_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.PRACTICE_PATTERNS]
    
    def remove_practice_headers_footers(self, text_lines: List[str]) -> List[str]:
        """
        Universal header/footer removal to clean practice information from consent forms
        
        Args:
            text_lines: List of text lines from the document
            
        Returns:
            List of text lines with practice headers/footers removed
        """
        cleaned_lines = []
        
        for line in text_lines:
            # Skip empty lines
            if not line.strip():
                continue
            
            # Check if line matches any practice information pattern
            is_practice_info = self._is_practice_information(line)
            
            if not is_practice_info:
                # Check for lines that combine practice info with form titles
                if self._has_mixed_practice_content(line):
                    # Extract just the form title part
                    extracted_content = self._extract_form_content(line)
                    if extracted_content:
                        cleaned_lines.append(extracted_content)
                    continue
                
                # Normal content line - keep it
                cleaned_lines.append(line)
        
        return cleaned_lines
    
    def _is_practice_information(self, line: str) -> bool:
        """Check if a line contains practice information that should be removed"""
        line = line.strip()
        
        # Check against compiled patterns
        for pattern in self.compiled_patterns:
            if pattern.match(line):
                return True
        
        # Additional checks for practice-specific content
        line_lower = line.lower()
        practice_keywords = [
            'smile solutions', 'dental office', 'family dentistry', 
            'cosmetic dentistry', 'orthodontics', 'endodontics',
            'periodontics', 'oral surgery', 'implant dentistry'
        ]
        
        return any(keyword in line_lower for keyword in practice_keywords)
    
    def _has_mixed_practice_content(self, line: str) -> bool:
        """Check if line contains both practice info and form content"""
        line_lower = line.lower()
        
        # Look for lines that combine practice info with form titles
        has_practice_markers = any(marker in line_lower for marker in ['smile@', 'www.'])
        has_form_content = 'informed consent' in line_lower
        
        return has_practice_markers and has_form_content
    
    def _extract_form_content(self, line: str) -> str:
        """Extract form content from a line that has mixed practice/form information"""
        # Extract just the informed consent part
        consent_match = re.search(r'(informed\\s+consent[^•]*)', line, re.IGNORECASE)
        if consent_match:
            return consent_match.group(1).strip()
        
        return ""
    
    def clean_content_string(self, content: str) -> str:
        """
        Clean practice information from a content string
        
        Args:
            content: String content to clean
            
        Returns:
            Cleaned string content
        """
        if not content:
            return content
        
        # Split into lines, clean each line, then rejoin
        lines = content.split('\\n')
        cleaned_lines = self.remove_practice_headers_footers(lines)
        
        # Clean up extra whitespace
        content = '\\n'.join(cleaned_lines)
        content = re.sub(r'\\s+', ' ', content).strip()
        
        return content
    
    def is_likely_header_footer(self, line: str, line_index: int, total_lines: int) -> bool:
        """
        Determine if a line is likely a header or footer based on position and content
        
        Args:
            line: The text line to check
            line_index: Position of the line in the document (0-based)
            total_lines: Total number of lines in the document
            
        Returns:
            True if the line is likely a header or footer
        """
        # Check if line is in header/footer position (first or last 5% of document)
        header_threshold = max(1, int(total_lines * 0.05))
        footer_threshold = total_lines - header_threshold
        
        is_header_position = line_index < header_threshold
        is_footer_position = line_index >= footer_threshold
        
        # If in header/footer position and contains practice info, likely header/footer
        if (is_header_position or is_footer_position) and self._is_practice_information(line):
            return True
        
        # Check for other header/footer indicators
        line_lower = line.lower().strip()
        header_footer_indicators = [
            'page ', 'of ', '©', 'copyright', 'all rights reserved',
            'confidential', 'proprietary', 'revised', 'version',
            'form id', 'document id'
        ]
        
        return any(indicator in line_lower for indicator in header_footer_indicators)