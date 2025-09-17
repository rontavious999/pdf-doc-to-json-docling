"""
Field Normalizer Module

Handles field name normalization and key generation.
"""

import re
import unicodedata
from typing import Dict, Any


class FieldNormalizer:
    """Normalize field names and generate proper keys"""
    
    def normalize_field_name(self, field_name: str, context_line: str = "") -> str:
        """Normalize field names to match expected patterns"""
        field_lower = field_name.lower().strip()
        
        # Handle common field name variations with exact reference matching
        field_mappings = {
            # Exact matches for key NPF fields
            "today's date": "Today's Date",
            "todays date": "Today's Date", 
            "date": "Today's Date",
            "first": "First Name",
            "first name": "First Name",
            "patient name": "First Name",  # Sometimes appears as this
            "mi": "Middle Initial",
            "middle initial": "Middle Initial", 
            "m.i.": "Middle Initial",
            "last": "Last Name",
            "last name": "Last Name",
            "nickname": "Nickname",
            "nick name": "Nickname",
            "street": "Street",
            "apt/unit/suite": "Apt/Unit/Suite",
            "apartment": "Apt/Unit/Suite",
            "unit": "Apt/Unit/Suite", 
            "suite": "Apt/Unit/Suite",
            "city": "City",
            "state": "State",
            "zip": "Zip",
            "zip code": "Zip",
            "mobile": "Mobile",
            "mobile phone": "Mobile",
            "home": "Home", 
            "home phone": "Home",
            "work": "Work",
            "work phone": "Work",
            "e-mail": "E-Mail",
            "email": "E-Mail",
            "drivers license #": "Drivers License #",
            "drivers license": "Drivers License #",
            "driver's license": "Drivers License #",
            "license": "Drivers License #",
            
            # SSN variations
            "ssn": "Social Security No.",
            "social security no.": "Social Security No.",
            "social security": "Social Security No.",
            "social security number": "Social Security No.",
            
            # Date of birth variations  
            "date of birth": "Date of Birth",
            "birth date": "Date of Birth",
            "birthdate": "Date of Birth",
            "dob": "Date of Birth",
            "born": "Date of Birth",
            
            # Employment fields
            "patient employed by": "Patient Employed By",
            "employed by": "Patient Employed By",
            "employer": "Patient Employed By",
            "occupation": "Occupation",
            "job": "Occupation",
            
            # Emergency contact fields
            "in case of emergency, who should be notified": "In case of emergency, who should be notified",
            "emergency contact": "In case of emergency, who should be notified",
            "emergency": "In case of emergency, who should be notified",
            "notify": "In case of emergency, who should be notified",
            
            "relationship to patient": "Relationship to Patient",
            "relationship": "Relationship to Patient",
            "mobile phone": "Mobile Phone", 
            "home phone": "Home Phone",
            
            # Insurance fields
            "name of insured": "Name of Insured",
            "insured": "Name of Insured",
            "birthdate": "Birthdate",  # In insurance context
            "insurance company": "Insurance Company",
            "dental plan name": "Dental Plan Name",
            "plan name": "Dental Plan Name",
            "plan/group number": "Plan/Group Number",
            "group number": "Plan/Group Number",
            "id number": "ID Number",
            "patient relationship to insured": "Patient Relationship to Insured",
            
            # Children/minors fields
            "name of school": "Name of School",
            "school": "Name of School",
            "employer (if different from above)": "Employer (if different from above)",
            
            # Signature section
            "initial": "Initial",
            "initials": "Initial",
            "signature": "Signature",
            "date signed": "Date Signed",
        }
        
        # First try exact mapping
        if field_lower in field_mappings:
            return field_mappings[field_lower]
        
        # Handle numbered fields that should maintain their numbers
        number_match = re.search(r'(.+?)(\d+)$', field_name.strip())
        if number_match:
            base_name = number_match.group(1).strip()
            number = number_match.group(2)
            
            # Normalize base name and add number back
            base_normalized = field_mappings.get(base_name.lower(), base_name)
            return f"{base_normalized}"  # Don't add number in title for now
        
        # Clean up and title case for unrecognized fields
        cleaned = re.sub(r'[^\w\s]', ' ', field_name)
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        
        if cleaned:
            return cleaned.title()
        
        return field_name.strip() or "Field"
    
    def generate_field_key(self, title: str, section: str = "") -> str:
        """Generate field key from title with reference-accurate mappings"""
        title_lower = title.lower().strip()
        
        # Reference-exact key mappings for critical fields
        key_mappings = {
            "today's date": "todays_date",
            "first name": "first_name", 
            "middle initial": "mi",
            "last name": "last_name",
            "nickname": "nickname",
            "street": "street",
            "apt/unit/suite": "apt_unit_suite",
            "city": "city",
            "state": "state", 
            "zip": "zip",
            "mobile": "mobile",
            "home": "home",
            "work": "work",
            "e-mail": "e_mail",
            "drivers license #": "drivers_license",
            "social security no.": "ssn",
            "date of birth": "date_of_birth",
            "patient employed by": "patient_employed_by",
            "occupation": "occupation",
            "sex": "sex",
            "marital status": "marital_status",
            "in case of emergency, who should be notified": "in_case_of_emergency_who_should_be_notified",
            "relationship to patient": "relationship_to_patient",
            "mobile phone": "mobile_phone", 
            "home phone": "home_phone",
            "is the patient a minor?": "is_the_patient_a_minor",
            "full-time student": "full_time_student",
            "name of school": "name_of_school",
            "what is your preferred method of contact": "what_is_your_preferred_method_of_contact",
            "signature": "signature",
            "initial": "initials",
            "date signed": "date_signed"
        }
        
        # Try exact mapping first
        if title_lower in key_mappings:
            return key_mappings[title_lower]
        
        # Handle numbered fields with section context
        if any(word in title_lower for word in ['name of insured', 'birthdate', 'insurance company', 'dental plan name']):
            base_key = self._slugify(title)
            if 'secondary' in section.lower():
                return f"{base_key}_2"
            return base_key
        
        # Default slugification
        return self._slugify(title)
    
    def _slugify(self, text: str, fallback: str = "field") -> str:
        """Convert text to a valid key slug"""
        if not text or not text.strip():
            return fallback
        
        # Normalize unicode characters
        text = unicodedata.normalize('NFKD', text)
        
        # Remove special characters and spaces, convert to lowercase
        slug = re.sub(r'[^\w\s-]', '', text.lower())
        slug = re.sub(r'[-\s]+', '_', slug)
        return slug.strip('_') or fallback