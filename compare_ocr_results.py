#!/usr/bin/env python3
"""
Script to compare OCR ON vs OCR OFF results and generate comparison table
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Any, Tuple
import difflib


class JSONComparer:
    """Compare JSON outputs from OCR ON vs OCR OFF"""
    
    def __init__(self, ocr_on_dir: str = "output_ocr_on", ocr_off_dir: str = "output_ocr_off"):
        self.ocr_on_dir = Path(ocr_on_dir)
        self.ocr_off_dir = Path(ocr_off_dir)
        
    def load_json_file(self, file_path: Path) -> List[Dict[str, Any]]:
        """Load JSON file and return the content"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading {file_path}: {e}")
            return []
    
    def calculate_extraction_score(self, json_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate extraction quality score for a JSON output"""
        if not json_data:
            return {
                "total_fields": 0,
                "filled_fields": 0,
                "field_types": {},
                "sections": set(),
                "extraction_score": 0.0,
                "quality_indicators": {}
            }
        
        total_fields = len(json_data)
        filled_fields = 0
        field_types = {}
        sections = set()
        
        # Quality indicators
        has_signature = False
        has_patient_info = False
        has_contact_info = False
        unique_keys = set()
        duplicate_keys = 0
        
        for field in json_data:
            # Count field types
            field_type = field.get("type", "unknown")
            field_types[field_type] = field_types.get(field_type, 0) + 1
            
            # Track sections
            section = field.get("section", "Unknown")
            sections.add(section)
            
            # Check for key uniqueness
            key = field.get("key", "")
            if key in unique_keys:
                duplicate_keys += 1
            else:
                unique_keys.add(key)
            
            # Check if field has meaningful content
            title = field.get("title", "").strip()
            if title and len(title) > 2:
                filled_fields += 1
            
            # Quality indicators
            if field_type == "signature":
                has_signature = True
            if "patient" in title.lower() or "name" in title.lower():
                has_patient_info = True
            if "email" in title.lower() or "phone" in title.lower() or "address" in title.lower():
                has_contact_info = True
        
        # Calculate extraction score (0-100)
        if total_fields == 0:
            extraction_score = 0.0
        else:
            base_score = (filled_fields / total_fields) * 60  # 60% for field coverage
            structure_score = min(len(sections) * 5, 20)  # 20% for section diversity
            quality_score = 0
            
            # Bonus points for quality indicators
            if has_signature:
                quality_score += 5
            if has_patient_info:
                quality_score += 5
            if has_contact_info:
                quality_score += 5
            if duplicate_keys == 0:
                quality_score += 5
            
            extraction_score = min(base_score + structure_score + quality_score, 100.0)
        
        return {
            "total_fields": total_fields,
            "filled_fields": filled_fields,
            "field_types": field_types,
            "sections": sections,
            "extraction_score": round(extraction_score, 1),
            "quality_indicators": {
                "has_signature": has_signature,
                "has_patient_info": has_patient_info,
                "has_contact_info": has_contact_info,
                "duplicate_keys": duplicate_keys,
                "unique_sections": len(sections)
            }
        }
    
    def compare_json_content(self, ocr_on_data: List[Dict], ocr_off_data: List[Dict]) -> Dict[str, Any]:
        """Compare content between OCR ON and OCR OFF versions"""
        # Extract field titles for comparison
        ocr_on_titles = set(field.get("title", "").strip() for field in ocr_on_data)
        ocr_off_titles = set(field.get("title", "").strip() for field in ocr_off_data)
        
        # Remove empty titles
        ocr_on_titles.discard("")
        ocr_off_titles.discard("")
        
        # Find differences
        only_in_ocr_on = ocr_on_titles - ocr_off_titles
        only_in_ocr_off = ocr_off_titles - ocr_on_titles
        common_titles = ocr_on_titles & ocr_off_titles
        
        return {
            "common_fields": len(common_titles),
            "only_in_ocr_on": len(only_in_ocr_on),
            "only_in_ocr_off": len(only_in_ocr_off),
            "ocr_on_total": len(ocr_on_titles),
            "ocr_off_total": len(ocr_off_titles),
            "fields_only_ocr_on": list(only_in_ocr_on)[:5],  # Show first 5
            "fields_only_ocr_off": list(only_in_ocr_off)[:5]  # Show first 5
        }
    
    def compare_all_pdfs(self) -> List[Dict[str, Any]]:
        """Compare all PDF outputs and generate comparison data"""
        results = []
        
        # Get list of JSON files (excluding summary files)
        ocr_on_files = [f for f in self.ocr_on_dir.glob("*.json") if "summary" not in f.name]
        
        for ocr_on_file in ocr_on_files:
            pdf_name = ocr_on_file.stem
            ocr_off_file = self.ocr_off_dir / ocr_on_file.name
            
            if not ocr_off_file.exists():
                print(f"Warning: OCR OFF version not found for {pdf_name}")
                continue
            
            # Load both versions
            ocr_on_data = self.load_json_file(ocr_on_file)
            ocr_off_data = self.load_json_file(ocr_off_file)
            
            # Calculate scores
            ocr_on_score = self.calculate_extraction_score(ocr_on_data)
            ocr_off_score = self.calculate_extraction_score(ocr_off_data)
            
            # Compare content
            content_diff = self.compare_json_content(ocr_on_data, ocr_off_data)
            
            # Determine which is better
            if ocr_on_score["extraction_score"] > ocr_off_score["extraction_score"]:
                better = "OCR ON"
                score_diff = ocr_on_score["extraction_score"] - ocr_off_score["extraction_score"]
            elif ocr_off_score["extraction_score"] > ocr_on_score["extraction_score"]:
                better = "OCR OFF"
                score_diff = ocr_off_score["extraction_score"] - ocr_on_score["extraction_score"]
            else:
                better = "TIE"
                score_diff = 0.0
            
            results.append({
                "pdf_name": pdf_name,
                "ocr_on_score": ocr_on_score["extraction_score"],
                "ocr_off_score": ocr_off_score["extraction_score"],
                "better": better,
                "score_difference": round(score_diff, 1),
                "ocr_on_fields": ocr_on_score["total_fields"],
                "ocr_off_fields": ocr_off_score["total_fields"],
                "ocr_on_sections": len(ocr_on_score["sections"]),
                "ocr_off_sections": len(ocr_off_score["sections"]),
                "content_diff": content_diff,
                "detailed_scores": {
                    "ocr_on": ocr_on_score,
                    "ocr_off": ocr_off_score
                }
            })
        
        return results
    
    def generate_comparison_table(self, results: List[Dict[str, Any]]) -> str:
        """Generate a markdown table with comparison results"""
        table = "# OCR ON vs OCR OFF Comparison Results\n\n"
        table += "| PDF File | OCR ON Score | OCR OFF Score | Better | Score Diff | OCR ON Fields | OCR OFF Fields |\n"
        table += "|----------|--------------|---------------|--------|------------|---------------|----------------|\n"
        
        for result in results:
            table += f"| {result['pdf_name']} | {result['ocr_on_score']} | {result['ocr_off_score']} | "
            table += f"**{result['better']}** | {result['score_difference']} | {result['ocr_on_fields']} | {result['ocr_off_fields']} |\n"
        
        # Add summary statistics
        ocr_on_wins = sum(1 for r in results if r['better'] == 'OCR ON')
        ocr_off_wins = sum(1 for r in results if r['better'] == 'OCR OFF')
        ties = sum(1 for r in results if r['better'] == 'TIE')
        
        avg_ocr_on = sum(r['ocr_on_score'] for r in results) / len(results) if results else 0
        avg_ocr_off = sum(r['ocr_off_score'] for r in results) / len(results) if results else 0
        
        table += f"\n## Summary\n\n"
        table += f"- **Total PDFs tested:** {len(results)}\n"
        table += f"- **OCR ON wins:** {ocr_on_wins}\n"
        table += f"- **OCR OFF wins:** {ocr_off_wins}\n"
        table += f"- **Ties:** {ties}\n"
        table += f"- **Average OCR ON score:** {avg_ocr_on:.1f}\n"
        table += f"- **Average OCR OFF score:** {avg_ocr_off:.1f}\n"
        
        if avg_ocr_on > avg_ocr_off:
            table += f"- **Overall winner:** OCR ON (by {avg_ocr_on - avg_ocr_off:.1f} points)\n"
        elif avg_ocr_off > avg_ocr_on:
            table += f"- **Overall winner:** OCR OFF (by {avg_ocr_off - avg_ocr_on:.1f} points)\n"
        else:
            table += f"- **Overall result:** TIE\n"
        
        return table
    
    def generate_detailed_report(self, results: List[Dict[str, Any]]) -> str:
        """Generate a detailed analysis report"""
        report = "# Detailed OCR Comparison Analysis\n\n"
        
        for result in results:
            report += f"## {result['pdf_name']}\n\n"
            
            # Scores
            report += f"- **OCR ON Score:** {result['ocr_on_score']} ({result['ocr_on_fields']} fields, {result['ocr_on_sections']} sections)\n"
            report += f"- **OCR OFF Score:** {result['ocr_off_score']} ({result['ocr_off_fields']} fields, {result['ocr_off_sections']} sections)\n"
            report += f"- **Winner:** {result['better']} (difference: {result['score_difference']})\n\n"
            
            # Content differences
            diff = result['content_diff']
            report += f"### Content Analysis\n"
            report += f"- **Common fields:** {diff['common_fields']}\n"
            report += f"- **Fields only in OCR ON:** {diff['only_in_ocr_on']}\n"
            report += f"- **Fields only in OCR OFF:** {diff['only_in_ocr_off']}\n"
            
            if diff['fields_only_ocr_on']:
                report += f"- **Sample OCR ON exclusive fields:** {', '.join(diff['fields_only_ocr_on'])}\n"
            
            if diff['fields_only_ocr_off']:
                report += f"- **Sample OCR OFF exclusive fields:** {', '.join(diff['fields_only_ocr_off'])}\n"
            
            report += "\n"
        
        return report


def main():
    """Main comparison function"""
    print("Starting OCR ON vs OCR OFF comparison...")
    
    comparer = JSONComparer()
    results = comparer.compare_all_pdfs()
    
    if not results:
        print("No comparison results found. Make sure both output directories exist and contain JSON files.")
        return
    
    # Generate comparison table
    table = comparer.generate_comparison_table(results)
    
    # Generate detailed report
    detailed_report = comparer.generate_detailed_report(results)
    
    # Save results
    with open("ocr_comparison_table.md", 'w', encoding='utf-8') as f:
        f.write(table)
    
    with open("ocr_detailed_analysis.md", 'w', encoding='utf-8') as f:
        f.write(detailed_report)
    
    # Save raw results as JSON
    with open("ocr_comparison_data.json", 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, default=str)
    
    # Print summary to console
    print(f"\n{table}")
    
    print(f"\n✓ Comparison complete!")
    print(f"  - Summary table saved to: ocr_comparison_table.md")
    print(f"  - Detailed analysis saved to: ocr_detailed_analysis.md")
    print(f"  - Raw data saved to: ocr_comparison_data.json")


if __name__ == "__main__":
    main()