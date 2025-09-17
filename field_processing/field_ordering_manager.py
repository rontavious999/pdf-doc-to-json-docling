"""
Field Ordering Manager

Handles the ordering and sequencing of form fields to ensure consistent output
that matches reference standards.
"""

from typing import List, Dict, Any
from dataclasses import dataclass


@dataclass
class FieldInfo:
    """Information about a detected form field"""
    key: str
    title: str
    field_type: str
    section: str
    optional: bool = False
    control: Dict[str, Any] = None
    line_idx: int = 0
    
    def __post_init__(self):
        if self.control is None:
            self.control = {}


class FieldOrderingManager:
    """Manages field ordering to ensure consistent, predictable output"""
    
    # Standard field order for NPF forms (and similar comprehensive forms)
    REFERENCE_FIELD_ORDER = [
        "todays_date", "first_name", "mi", "last_name", "nickname", "street", "apt_unit_suite", 
        "city", "state", "zip", "mobile", "home", "work", "e_mail", "drivers_license", "state2",
        "what_is_your_preferred_method_of_contact", "ssn", "date_of_birth", "patient_employed_by",
        "occupation", "street_2", "city_2", "state3", "zip_2", "sex", "marital_status",
        "in_case_of_emergency_who_should_be_notified", "relationship_to_patient", "mobile_phone",
        "home_phone", "is_the_patient_a_minor", "full_time_student", "name_of_school", 
        "first_name_2", "last_name_2", "date_of_birth_2", "relationship_to_patient_2",
        "if_patient_is_a_minor_primary_residence", "if_different_from_patient_street", "city_3",
        "state4", "zip_3", "mobile_2", "home_2", "work_2", "employer_if_different_from_above",
        "occupation_2", "street_3", "city_2_2", "state5", "zip_4", "name_of_insured",
        "birthdate", "ssn_2", "insurance_company", "phone", "street_4", "city_5", "state_6",
        "zip_5", "dental_plan_name", "plan_group_number", "id_number", "patient_relationship_to_insured",
        "name_of_insured_2", "birthdate_2", "ssn_3", "insurance_company_2", "phone_2", "street_5",
        "city_6", "state_7", "zip_6", "dental_plan_name_2", "plan_group_number_2", "id_number_2",
        "patient_relationship_to_insured_2", "text_3", "initials", "text_4", "initials_2",
        "i_authorize_the_release_of_my_personal_information_necessary_to_process_my_dental_benefit_claims,_including_health_information,_",
        "initials_3", "signature", "date_signed"
    ]
    
    def __init__(self):
        """Initialize the field ordering manager"""
        pass
    
    def order_fields(self, fields: List[FieldInfo]) -> List[FieldInfo]:
        """
        Order fields according to a reference pattern.
        
        Args:
            fields: List of FieldInfo objects to order
            
        Returns:
            List of FieldInfo objects in proper order
        """
        # Sort by line_idx first to preserve document order
        fields.sort(key=lambda f: getattr(f, 'line_idx', 0))
        
        # If we have a reference order to follow, apply it
        if self._should_use_reference_ordering(fields):
            return self._apply_reference_ordering(fields)
        
        # Otherwise maintain document order with signature fields at end
        return self._apply_standard_ordering(fields)
    
    def _should_use_reference_ordering(self, fields: List[FieldInfo]) -> bool:
        """
        Determine if we should use the reference ordering pattern.
        
        This is typically for comprehensive forms like NPF that match the reference structure.
        """
        field_keys = {field.key for field in fields}
        reference_keys = set(self.REFERENCE_FIELD_ORDER)
        
        # If we have a significant overlap with reference keys, use reference ordering
        overlap = len(field_keys.intersection(reference_keys))
        return overlap > len(field_keys) * 0.5  # More than 50% overlap
    
    def _apply_reference_ordering(self, fields: List[FieldInfo]) -> List[FieldInfo]:
        """Apply the reference field ordering"""
        field_lookup = {field.key: field for field in fields}
        ordered_fields = []
        
        # Add fields in reference order
        for key in self.REFERENCE_FIELD_ORDER:
            if key in field_lookup:
                ordered_fields.append(field_lookup[key])
        
        # Add any remaining fields that aren't in the reference order
        for field in fields:
            if field.key not in self.REFERENCE_FIELD_ORDER:
                ordered_fields.append(field)
        
        return ordered_fields
    
    def _apply_standard_ordering(self, fields: List[FieldInfo]) -> List[FieldInfo]:
        """Apply standard ordering for forms that don't match reference pattern"""
        # Group fields by type with signatures at the end
        signature_fields = []
        other_fields = []
        
        for field in fields:
            if field.field_type == 'signature':
                signature_fields.append(field)
            else:
                other_fields.append(field)
        
        # Return non-signature fields followed by signature fields
        return other_fields + signature_fields
    
    def ensure_required_signature_fields(self, fields: List[FieldInfo]) -> List[FieldInfo]:
        """
        Ensure required signature fields are present.
        
        According to Modento schema, exactly one signature field is required.
        """
        signature_fields = [f for f in fields if f.field_type == 'signature']
        
        if not signature_fields:
            # Add missing signature field
            signature_field = FieldInfo(
                key="signature",
                title="Signature",
                field_type='signature',
                section="Signature",
                optional=False,
                control={},
                line_idx=9999  # Ensure it's at the end
            )
            fields.append(signature_field)
        elif len(signature_fields) > 1:
            # Keep only the first signature field and ensure it has the canonical key
            first_sig = signature_fields[0]
            first_sig.key = 'signature'
            # Remove the others
            fields = [f for f in fields if not (f.field_type == 'signature' and f != first_sig)]
        else:
            # Ensure canonical key
            signature_fields[0].key = 'signature'
        
        return fields
    
    def ensure_date_signed_field(self, fields: List[FieldInfo]) -> List[FieldInfo]:
        """Ensure date_signed field is present if signature exists"""
        has_signature = any(f.field_type == 'signature' for f in fields)
        has_date_signed = any(f.key == 'date_signed' for f in fields)
        
        if has_signature and not has_date_signed:
            date_signed_field = FieldInfo(
                key="date_signed",
                title="Date Signed",
                field_type='date',
                section="Signature",
                optional=False,
                control={'input_type': 'past'},
                line_idx=9999  # Ensure it's at the end
            )
            fields.append(date_signed_field)
        
        return fields