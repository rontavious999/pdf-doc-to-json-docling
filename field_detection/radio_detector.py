"""
Radio Detector Module

Handles radio button and checkbox detection and option extraction.
"""

import re
from typing import List, Dict, Any, Optional, Tuple


class RadioDetector:
    """Detect radio buttons, checkboxes and their options"""
    
    # Centralized checkbox character class
    CHECKBOX_CHAR_CLASS = r"□■☐☑✅◉●○•\-\–\*\[\]\(\)"
    
    def detect_radio_question(self, line: str) -> Optional[Tuple[str, List[Dict[str, Any]]]]:
        """Detect radio button questions and extract options"""
        line_lower = line.lower()
        
        # Common radio button patterns with exact reference matching
        radio_patterns = [
            # Sex/Gender selection
            {
                'pattern': r'sex.*?(?:male|female)',
                'title': 'Sex',
                'options': [
                    {"name": "Male", "value": "male"},
                    {"name": "Female", "value": "female"}
                ]
            },
            # Marital status
            {
                'pattern': r'marital.*?status',
                'title': 'Marital Status',
                'options': [
                    {"name": "Married", "value": "Married"},
                    {"name": "Single", "value": "Single"},
                    {"name": "Divorced", "value": "Divorced"},
                    {"name": "Separated", "value": "Separated"},
                    {"name": "Widowed", "value": "Widowed"}
                ]
            },
            # Yes/No questions
            {
                'pattern': r'is.*?patient.*?minor',
                'title': 'Is the Patient a Minor?',
                'options': [
                    {"name": "Yes", "value": True},
                    {"name": "No", "value": False}
                ]
            },
            {
                'pattern': r'full.*?time.*?student',
                'title': 'Full-time Student',
                'options': [
                    {"name": "Yes", "value": True},
                    {"name": "No", "value": False}
                ]
            },
            # Preferred contact method
            {
                'pattern': r'preferred.*?method.*?contact',
                'title': 'What Is Your Preferred Method Of Contact',
                'options': [
                    {"name": "Mobile Phone", "value": "Mobile Phone"},
                    {"name": "Home Phone", "value": "Home Phone"},
                    {"name": "Work Phone", "value": "Work Phone"},
                    {"name": "E-mail", "value": "E-mail"}
                ]
            },
            # Relationship patterns
            {
                'pattern': r'relationship.*?to.*?patient',
                'title': 'Relationship To Patient',
                'options': [
                    {"name": "Self", "value": "Self"},
                    {"name": "Spouse", "value": "Spouse"},
                    {"name": "Parent", "value": "Parent"},
                    {"name": "Other", "value": "Other"}
                ]
            },
            # Primary residence for minors
            {
                'pattern': r'primary.*?residence',
                'title': 'If Patient Is A Minor, Primary Residence',
                'options': [
                    {"name": "Both Parents", "value": "Both Parents"},
                    {"name": "Mom", "value": "Mom"},
                    {"name": "Dad", "value": "Dad"},
                    {"name": "Step Parent", "value": "Step Parent"},
                    {"name": "Shared Custody", "value": "Shared Custody"},
                    {"name": "Guardian", "value": "Guardian"}
                ]
            },
            # Insurance authorization
            {
                'pattern': r'authorize.*?release.*?personal.*?information',
                'title': 'I authorize the release of my personal information necessary to process my dental benefit claims, including health information, diagnosis, and records of any treatment or exam rendered. I hereby authorize payment of benefits directly to this dental office otherwise payable to me.',
                'options': [
                    {"name": "Yes", "value": True},
                    {"name": "No", "value": False}
                ]
            }
        ]
        
        # Check each pattern
        for pattern_info in radio_patterns:
            if re.search(pattern_info['pattern'], line_lower):
                return pattern_info['title'], pattern_info['options']
        
        return None
    
    def detect_radio_options_universal(self, text_lines: List[str], start_idx: int) -> Tuple[Optional[str], List[Dict[str, Any]], int]:
        """Detect radio button questions and their options - enhanced for NPF patterns"""
        
        if start_idx >= len(text_lines):
            return None, [], start_idx
            
        line = text_lines[start_idx]
        
        # First, try predefined patterns - this ensures reference accuracy
        predefined_result = self.detect_radio_question(line)
        if predefined_result:
            question, options = predefined_result
            return question, options, start_idx + 1
        
        # Enhanced Pattern 1: Question with checkboxes on same line (like primary residence)
        checkbox_pattern = r'([^□☐!]+?)(?:□|☐|!)([^□☐!]+?)(?:□|☐|!)([^□☐!]*)'
        match = re.search(checkbox_pattern, line)
        if match:
            question = match.group(1).strip().rstrip(':')
            if len(question) >= 5:  # Must be substantial question
                # Extract options from the line
                options = []
                option_parts = re.split(rf'[{self.CHECKBOX_CHAR_CLASS}]', line)[1:]  # Skip the question part
                for part in option_parts:
                    option_text = part.strip()
                    if option_text and len(option_text) > 0:
                        # Clean up option text
                        option_text = option_text.strip('(),. ')
                        if option_text and option_text not in ['', ' ']:
                            value = option_text.lower()
                            if value in ['yes', 'true']:
                                value = True
                            elif value in ['no', 'false']:
                                value = False
                            else:
                                value = option_text  # Keep original text for other options
                            options.append({"name": option_text, "value": value})
                
                if len(options) >= 2:
                    return question, options, start_idx + 1

        # Enhanced Pattern 2: Question followed by options on subsequent lines
        # This handles "Is the patient a Minor?" and "What is your preferred method of contact?"
        if (line.strip().endswith('?') or 
            'preferred method of contact' in line.lower() or
            'full-time student' in line.lower()) and not line.strip().startswith('##'):
            
            question = line.strip().rstrip('?').strip()
            if len(question) < 5:
                return None, [], start_idx
                
            options = []
            next_idx = start_idx + 1
            
            # Look ahead for options in next lines
            while next_idx < len(text_lines) and len(options) < 6:  # Max 6 options
                next_line = text_lines[next_idx]
                
                # Stop if we hit another question or section
                if (next_line.strip().endswith('?') or 
                    next_line.startswith('##') or
                    len(next_line.strip()) > 60):  # Too long to be an option
                    break
                
                # Look for checkbox or bullet options
                if any(char in next_line for char in '□☐!●○•'):
                    # Extract option text
                    option_parts = re.split(rf'[{self.CHECKBOX_CHAR_CLASS}]', next_line)
                    for part in option_parts[1:]:  # Skip empty first part
                        option_text = part.strip()
                        if option_text and len(option_text) > 0:
                            option_text = option_text.strip('(),. ')
                            if option_text:
                                value = option_text
                                # Special handling for Yes/No
                                if value.lower() in ['yes', 'true']:
                                    value = True
                                elif value.lower() in ['no', 'false']:
                                    value = False
                                options.append({"name": option_text, "value": value})
                
                next_idx += 1
            
            if len(options) >= 2:
                return question, options, next_idx
        
        # Pattern 3: Enhanced inline options detection
        # Look for patterns like "Male/Female", "Yes/No", "Check one:"
        inline_patterns = [
            (r'(male)\s*/\s*(female)', [
                {"name": "Male", "value": "male"},
                {"name": "Female", "value": "female"}
            ]),
            (r'(yes)\s*/\s*(no)', [
                {"name": "Yes", "value": True},
                {"name": "No", "value": False}
            ]),
            (r'(married)\s*/\s*(single)\s*/\s*(divorced)', [
                {"name": "Married", "value": "Married"},
                {"name": "Single", "value": "Single"},
                {"name": "Divorced", "value": "Divorced"}
            ])
        ]
        
        line_lower = line.lower()
        for pattern, options in inline_patterns:
            if re.search(pattern, line_lower):
                # Extract question part before the options
                question = re.split(pattern, line, flags=re.IGNORECASE)[0].strip().rstrip(':')
                if len(question) >= 3:
                    return question, options, start_idx + 1
        
        return None, [], start_idx
    
    def get_radio_key_for_question(self, question: str, section: str) -> str:
        """Map radio questions to exact reference keys with section awareness"""
        question_lower = question.lower()
        
        # Reference-exact key mappings for radio questions
        key_mappings = {
            'what is your preferred method of contact': 'what_is_your_preferred_method_of_contact',
            'preferred method of contact': 'what_is_your_preferred_method_of_contact',
            'sex': 'sex',
            'marital status': 'marital_status',
            'is the patient a minor?': 'is_the_patient_a_minor',
            'is the patient a minor': 'is_the_patient_a_minor',
            'patient a minor': 'is_the_patient_a_minor',
            'full-time student': 'full_time_student',
            'full time student': 'full_time_student',
            'relationship to patient': 'relationship_to_patient_2' if 'minor' in section.lower() else 'relationship_to_patient',
            'if patient is a minor, primary residence': 'if_patient_is_a_minor_primary_residence',
            'primary residence': 'if_patient_is_a_minor_primary_residence',
            'i authorize the release of my personal information': 'i_authorize_the_release_of_my_personal_information_necessary_to_process_my_dental_benefit_claims,_including_health_information,_',
        }
        
        # Try exact matches first
        for key_phrase, mapped_key in key_mappings.items():
            if key_phrase in question_lower:
                return mapped_key
        
        # Fallback to slugified version
        return self._slugify(question)
    
    def _slugify(self, text: str, fallback: str = "field") -> str:
        """Convert text to a valid key slug"""
        if not text or not text.strip():
            return fallback
        
        # Remove special characters and spaces, convert to lowercase
        slug = re.sub(r'[^\w\s-]', '', text.lower())
        slug = re.sub(r'[-\s]+', '_', slug)
        return slug.strip('_') or fallback