# src/document_processor.py
import fitz  # PyMuPDF
import re
from typing import List, Dict, Optional
import logging

class DocumentProcessor:
    def __init__(self):
        self.heading_patterns = [
            r'^\d+\.?\s+[A-Z]',      # Numbered headings (1. Introduction)
            r'^[A-Z][A-Z\s]{5,}$',   # ALL CAPS headings
            r'^[A-Z][a-z]+(?:\s+[A-Z][a-z]*)*$',  # Title Case
            r'^(Chapter|Section|Part|Module)\s+\d+',  # Explicit sections
            r'^\d+\.\d+\s+',         # Subsection numbering (1.1, 2.3)
            r'^[IVX]+\.\s+',         # Roman numerals
        ]
        self.min_heading_font_size = 12
        self.min_content_length = 20
    
    def extract_sections(self, pdf_path: str) -> List[Dict]:
        """Extract sections from a PDF document with improved accuracy."""
        try:
            doc = fitz.open(pdf_path)
            sections = []
            current_section = None
            document_name = pdf_path.split("/")[-1]
            
            # Get document-wide font statistics for better heading detection
            font_stats = self._analyze_font_statistics(doc)
            
            for page_num in range(doc.page_count):
                page = doc[page_num]
                blocks = page.get_text("dict")["blocks"]
                
                for block in blocks:
                    if block.get("type") == 0:  # Text block
                        for line in block.get("lines", []):
                            for span in line.get("spans", []):
                                text = span["text"].strip()
                                if not text or len(text) < 3:
                                    continue
                                
                                # Enhanced heading detection
                                if self._is_heading_enhanced(span, text, font_stats):
                                    # Save previous section if it has meaningful content
                                    if current_section and len(current_section["content"].strip()) > self.min_content_length:
                                        current_section["content"] = self._clean_content(current_section["content"])
                                        sections.append(current_section)
                                    
                                    # Start new section
                                    current_section = {
                                        "document": document_name,
                                        "page_number": page_num + 1,
                                        "section_title": self._clean_title(text),
                                        "content": "",
                                        "font_size": span["size"],
                                        "is_bold": bool(span["flags"] & 0x04),
                                        "heading_level": self._determine_heading_level(span, text, font_stats)
                                    }
                                else:
                                    # Add to current section content
                                    if current_section:
                                        current_section["content"] += " " + text
            
            # Add final section
            if current_section and len(current_section["content"].strip()) > self.min_content_length:
                current_section["content"] = self._clean_content(current_section["content"])
                sections.append(current_section)
            
            doc.close()
            
            # Post-process sections for better quality
            sections = self._post_process_sections(sections)
            
            logging.info(f"Extracted {len(sections)} sections from {document_name}")
            return sections
            
        except Exception as e:
            logging.error(f"Error processing {pdf_path}: {e}")
            return []
    
    def _analyze_font_statistics(self, doc) -> Dict:
        """Analyze document font statistics for better heading detection."""
        font_sizes = []
        for page_num in range(min(5, doc.page_count)):  # Analyze first 5 pages
            page = doc[page_num]
            blocks = page.get_text("dict")["blocks"]
            
            for block in blocks:
                if block.get("type") == 0:
                    for line in block.get("lines", []):
                        for span in line.get("spans", []):
                            if span["text"].strip():
                                font_sizes.append(span["size"])
        
        if not font_sizes:
            return {"avg_size": 12, "max_size": 16, "common_size": 12}
        
        import statistics
        return {
            "avg_size": statistics.mean(font_sizes),
            "max_size": max(font_sizes),
            "common_size": statistics.mode(font_sizes) if font_sizes else 12,
            "sizes": sorted(set(font_sizes), reverse=True)
        }
    
    def _is_heading_enhanced(self, span: Dict, text: str, font_stats: Dict) -> bool:
        """Enhanced heading detection using multiple criteria."""
        font_size = span["size"]
        is_bold = bool(span["flags"] & 0x04)
        
        # Font size criteria (relative to document)
        if font_size > font_stats["avg_size"] + 2:
            return True
        
        # Bold and reasonable size
        if is_bold and font_size >= font_stats["common_size"] and len(text.split()) <= 15:
            return True
        
        # Pattern matching
        for pattern in self.heading_patterns:
            if re.match(pattern, text):
                return True
        
        # Structural indicators
        if (text.isupper() and len(text.split()) <= 8 and 
            font_size >= font_stats["common_size"]):
            return True
        
        return False
    
    def _determine_heading_level(self, span: Dict, text: str, font_stats: Dict) -> int:
        """Determine heading level (1-4) based on font size and patterns."""
        font_size = span["size"]
        
        # Level 1: Largest fonts or chapter indicators
        if (font_size >= font_stats["max_size"] - 1 or 
            re.match(r'^(Chapter|Module|Part)\s+\d+', text, re.IGNORECASE)):
            return 1
        
        # Level 2: Large fonts or numbered sections
        elif (font_size >= font_stats["avg_size"] + 3 or 
              re.match(r'^\d+\.?\s+[A-Z]', text)):
            return 2
        
        # Level 3: Medium fonts or subsections
        elif (font_size >= font_stats["avg_size"] + 1 or 
              re.match(r'^\d+\.\d+\s+', text)):
            return 3
        
        # Level 4: Everything else
        else:
            return 4
    
    def _clean_title(self, title: str) -> str:
        """Clean and normalize section titles."""
        # Remove extra whitespace
        title = re.sub(r'\s+', ' ', title).strip()
        
        # Remove trailing dots/colons
        title = re.sub(r'[.:]+$', '', title)
        
        # Capitalize properly if all caps
        if title.isupper() and len(title) > 10:
            title = title.title()
        
        return title
    
    def _clean_content(self, content: str) -> str:
        """Clean and normalize section content."""
        # Remove extra whitespace
        content = re.sub(r'\s+', ' ', content).strip()
        
        # Remove common OCR artifacts
        content = re.sub(r'[^\w\s.,;:!?()-]', ' ', content)
        content = re.sub(r'\s+', ' ', content)
        
        return content
    
    def _post_process_sections(self, sections: List[Dict]) -> List[Dict]:
        """Post-process sections for better quality."""
        processed_sections = []
        
        for section in sections:
            # Skip sections that are too short or likely noise
            if (len(section["content"].split()) < 10 or 
                len(section["section_title"]) < 3):
                continue
            
            # Merge very short sections with similar titles
            if (processed_sections and 
                len(section["content"].split()) < 30 and
                self._titles_similar(processed_sections[-1]["section_title"], 
                                   section["section_title"])):
                processed_sections[-1]["content"] += " " + section["content"]
                continue
            
            processed_sections.append(section)
        
        return processed_sections
    
    def _titles_similar(self, title1: str, title2: str) -> bool:
        """Check if two titles are similar."""
        # Simple similarity check
        words1 = set(title1.lower().split())
        words2 = set(title2.lower().split())
        
        if not words1 or not words2:
            return False
        
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        return intersection / union > 0.6
