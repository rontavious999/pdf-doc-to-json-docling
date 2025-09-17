#!/usr/bin/env python3
"""
Test the field detection module
"""

import sys
sys.path.append('.')

from field_detection.field_detector import FieldDetector
from field_detection.input_detector import InputDetector  
from field_detection.radio_detector import RadioDetector

def test_field_detection():
    """Test the field detection modules"""
    print("Testing Field Detection Modules")
    print("=" * 50)
    
    # Test field type detection
    detector = FieldDetector()
    input_detector = InputDetector()
    radio_detector = RadioDetector()
    
    # Test some basic field detection
    test_texts = [
        "Patient Name:",
        "Date of Birth:",
        "Sex: Male/Female",
        "Street ________________________________",
        "E-mail _________________________",
        "Is the patient a minor? Yes/No"
    ]
    
    for text in test_texts:
        field_type = detector.detect_field_type(text)
        print(f"[{field_type:>10}] {text}")
        
        if field_type == "input":
            input_type = input_detector.detect_input_type(text)
            print(f"              -> input_type: {input_type}")
        elif field_type == "radio":
            radio_result = radio_detector.detect_radio_question(text)
            if radio_result:
                question, options = radio_result
                print(f"              -> question: {question}")
                print(f"              -> options: {len(options)} options")
    
    print("\n[✓] Field detection module test completed!")

if __name__ == "__main__":
    test_field_detection()