#!/usr/bin/env python3
"""
Implement a targeted fix for field ordering by adjusting line indices
"""

def fix_field_ordering_issues(fields):
    """Apply specific fixes to resolve field ordering issues"""
    
    # Issue 1: relationship_to_patient_2 should be earlier in children section
    # Currently at position 47, should be around 37 (difference of ~10)
    
    # Find the relationship_to_patient_2 field
    relationship_field_idx = None
    for i, field in enumerate(fields):
        if field.key == 'relationship_to_patient_2':
            relationship_field_idx = i
            break
    
    if relationship_field_idx is not None:
        # Look for a good insertion point earlier in the children section
        # It should come after basic children info but before work address
        target_position = None
        for i, field in enumerate(fields):
            if field.section == "FOR CHILDREN/MINORS ONLY":
                # Look for fields like date_of_birth_2 or similar that should come before relationship
                if field.key in ['date_of_birth_2', 'if_patient_is_a_minor_primary_residence']:
                    target_position = i + 1
                    break
        
        if target_position is not None and target_position < relationship_field_idx:
            # Move the relationship field to the target position
            relationship_field = fields.pop(relationship_field_idx)
            fields.insert(target_position, relationship_field)
            print(f"Moved relationship_to_patient_2 from position {relationship_field_idx+1} to {target_position+1}")
    
    # Issue 2: Fix Secondary Dental Plan field ordering
    # insurance_company_2 and phone_2 should be positioned correctly
    
    # Find the start of Secondary Dental Plan section
    secondary_section_start = None
    for i, field in enumerate(fields):
        if field.section == "Secondary Dental Plan":
            secondary_section_start = i
            break
    
    if secondary_section_start is not None:
        # Collect all secondary dental plan fields
        secondary_fields = []
        i = secondary_section_start
        while i < len(fields) and fields[i].section == "Secondary Dental Plan":
            secondary_fields.append((i, fields[i]))
            i += 1
        
        # Sort secondary fields in desired order
        field_order = [
            'name_of_insured_2', 'birthdate_2', 'ssn_3', 'street_5', 'city_6', 
            'state_7', 'zip_6', 'dental_plan_name_2', 'plan_group_number_2',
            'insurance_company_2', 'phone_2', 'id_number_2', 'patient_relationship_to_insured_2'
        ]
        
        # Create ordered list of secondary fields
        ordered_secondary = []
        for desired_key in field_order:
            for idx, field in secondary_fields:
                if field.key == desired_key:
                    ordered_secondary.append((idx, field))
                    break
        
        # Add any remaining fields not in the order list
        used_indices = {idx for idx, _ in ordered_secondary}
        for idx, field in secondary_fields:
            if idx not in used_indices:
                ordered_secondary.append((idx, field))
        
        # Replace the secondary section with ordered fields
        if ordered_secondary:
            # Remove old secondary fields (in reverse order to maintain indices)
            for idx, _ in reversed(secondary_fields):
                fields.pop(idx)
            
            # Insert ordered secondary fields
            for i, (_, field) in enumerate(ordered_secondary):
                fields.insert(secondary_section_start + i, field)
            
            print(f"Reordered {len(secondary_fields)} Secondary Dental Plan fields")
    
    return fields

# This would be called from the main converter
# But for now, let's test it as a standalone fix