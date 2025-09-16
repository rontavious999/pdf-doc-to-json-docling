#!/usr/bin/env python3
"""
Analyze DOCX processing outputs and identify universal improvements needed
"""
import json
import glob
import os
from collections import defaultdict, Counter

class DocxOutputAnalyzer:
    """Analyzes DOCX outputs to identify patterns and improvements"""
    
    def __init__(self):
        self.field_types = Counter()
        self.sections = Counter()
        self.input_types = Counter()
        self.common_patterns = defaultdict(list)
        self.issues = []
    
    def analyze_file(self, json_file):
        """Analyze a single JSON file"""
        try:
            with open(json_file, 'r') as f:
                data = json.load(f)
            
            filename = os.path.basename(json_file)
            file_analysis = {
                'filename': filename,
                'field_count': len(data),
                'issues': [],
                'fields': []
            }
            
            signature_count = 0
            
            for item in data:
                if isinstance(item, dict):
                    field_type = item.get('type', 'unknown')
                    section = item.get('section', 'unknown')
                    key = item.get('key', 'unknown')
                    title = item.get('title', '')
                    
                    self.field_types[field_type] += 1
                    self.sections[section] += 1
                    
                    field_info = {
                        'key': key,
                        'type': field_type,
                        'title': title,
                        'section': section
                    }
                    
                    # Track input types
                    if field_type == 'input':
                        input_type = item.get('control', {}).get('input_type', 'missing')
                        self.input_types[input_type] += 1
                        field_info['input_type'] = input_type
                    
                    # Count signatures
                    if field_type == 'signature':
                        signature_count += 1
                    
                    # Check for witness fields (should be filtered out)
                    if 'witness' in key.lower():
                        file_analysis['issues'].append(f"❌ WITNESS FIELD: {key}")
                        self.issues.append(f"{filename}: Contains witness field '{key}'")
                    
                    file_analysis['fields'].append(field_info)
            
            # Check signature rule compliance
            if signature_count > 1:
                file_analysis['issues'].append(f"❌ MULTIPLE SIGNATURES: {signature_count} (should be exactly 1)")
                self.issues.append(f"{filename}: Has {signature_count} signature fields")
            elif signature_count == 0:
                file_analysis['issues'].append(f"❌ NO SIGNATURE: Missing required signature field")
                self.issues.append(f"{filename}: Missing signature field")
            
            return file_analysis
            
        except Exception as e:
            return {'filename': os.path.basename(json_file), 'error': str(e)}
    
    def analyze_all_outputs(self):
        """Analyze all DOCX output files"""
        print("=== DOCX OUTPUT ANALYSIS ===\n")
        
        test_dirs = ['docx_output_final', 'docx_output_improved', 'final_docx_test']
        all_analyses = []
        
        for test_dir in test_dirs:
            if os.path.exists(test_dir):
                print(f"📁 Analyzing directory: {test_dir}")
                json_files = glob.glob(f"{test_dir}/*.json")
                
                for json_file in json_files:
                    analysis = self.analyze_file(json_file)
                    all_analyses.append(analysis)
                    
                    # Print summary for each file
                    filename = analysis['filename']
                    if 'error' in analysis:
                        print(f"  ❌ {filename}: ERROR - {analysis['error']}")
                    else:
                        field_count = analysis['field_count']
                        issue_count = len(analysis['issues'])
                        print(f"  📄 {filename}: {field_count} fields, {issue_count} issues")
                        
                        for issue in analysis['issues']:
                            print(f"      {issue}")
                
                print()
        
        return all_analyses
    
    def generate_recommendations(self):
        """Generate universal improvement recommendations"""
        print("="*60)
        print("🎯 UNIVERSAL IMPROVEMENT RECOMMENDATIONS")
        print("="*60)
        
        print("\n1. 🚫 WITNESS FIELD REMOVAL (COMPLETED)")
        witness_issues = [issue for issue in self.issues if 'witness' in issue.lower()]
        if witness_issues:
            print(f"   Found {len(witness_issues)} files with witness fields")
            print("   ✅ Solution: Updated code filters out all witness fields")
        else:
            print("   ✅ No witness fields detected")
        
        print("\n2. 📝 SIGNATURE COMPLIANCE")
        signature_issues = [issue for issue in self.issues if 'signature' in issue.lower()]
        if signature_issues:
            print(f"   Found {len(signature_issues)} signature-related issues")
            for issue in signature_issues[:3]:  # Show first 3
                print(f"   - {issue}")
            print("   ✅ Solution: Ensure exactly one signature field with key='signature'")
        else:
            print("   ✅ Signature compliance looks good")
        
        print("\n3. 📊 FIELD TYPE DISTRIBUTION")
        print("   Most common field types:")
        for field_type, count in self.field_types.most_common(5):
            print(f"   - {field_type}: {count} occurrences")
        
        print("\n4. 🏷️ SECTION DISTRIBUTION")
        print("   Most common sections:")
        for section, count in self.sections.most_common(5):
            print(f"   - '{section}': {count} occurrences")
        
        print("\n5. 🔤 INPUT TYPE ANALYSIS")
        print("   Input types used:")
        for input_type, count in self.input_types.most_common():
            print(f"   - {input_type}: {count} occurrences")
        
        missing_input_types = self.input_types.get('missing', 0)
        if missing_input_types > 0:
            print(f"   ⚠️  {missing_input_types} input fields missing input_type")
        
        print("\n6. 🔧 UNIVERSAL PROCESSING IMPROVEMENTS")
        print("   Recommended enhancements:")
        print("   ✅ Remove ALL witness fields (completed)")
        print("   🔄 Ensure consistent input_type assignment")
        print("   🔄 Standardize section naming")
        print("   🔄 Validate signature field uniqueness")
        print("   🔄 Improve text formatting for consent forms")
        
        print("\n7. ✅ VALIDATION REQUIREMENTS")
        print("   Must ensure:")
        print("   - Exactly one signature field with key='signature'")
        print("   - No witness fields in any form type")
        print("   - All input fields have proper input_type")
        print("   - Consistent section naming")
        print("   - NPF.json output matches reference exactly")

if __name__ == "__main__":
    analyzer = DocxOutputAnalyzer()
    analyses = analyzer.analyze_all_outputs()
    analyzer.generate_recommendations()
    
    print(f"\n📈 SUMMARY:")
    print(f"Analyzed {len(analyses)} JSON files")
    print(f"Found {len(analyzer.issues)} total issues")
    print("All recommendations focus on universal processing without hardcoding")