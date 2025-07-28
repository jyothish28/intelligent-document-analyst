import fitz
import pandas as pd
from typing import List, Dict, Optional
import logging
import os

class PDFParser:
    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path
        self.doc = None
        self.metadata = {}
        
    def open_pdf(self) -> bool:
        """Open PDF document with error handling."""
        try:
            if not os.path.exists(self.pdf_path):
                logging.error(f"PDF file not found: {self.pdf_path}")
                return False
                
            self.doc = fitz.open(self.pdf_path)
            
            # Extract metadata
            self.metadata = {
                'title': self.doc.metadata.get('title', ''),
                'author': self.doc.metadata.get('author', ''),
                'subject': self.doc.metadata.get('subject', ''),
                'creator': self.doc.metadata.get('creator', ''),
                'producer': self.doc.metadata.get('producer', ''),
                'creation_date': self.doc.metadata.get('creationDate', ''),
                'modification_date': self.doc.metadata.get('modDate', ''),
                'page_count': self.doc.page_count,
                'encrypted': self.doc.is_encrypted,
                'pdf_version': getattr(self.doc, 'pdf_version', 'Unknown')
            }
            
            logging.info(f"Successfully opened PDF: {os.path.basename(self.pdf_path)}")
            logging.info(f"Pages: {self.doc.page_count}, Title: {self.metadata.get('title', 'N/A')}")
            
            return True
            
        except Exception as e:
            logging.error(f"Error opening PDF {self.pdf_path}: {e}")
            return False
    
    def close_pdf(self) -> None:
        """Close PDF document safely."""
        if self.doc:
            try:
                self.doc.close()
                self.doc = None
                logging.debug(f"Closed PDF: {os.path.basename(self.pdf_path)}")
            except Exception as e:
                logging.warning(f"Error closing PDF: {e}")
    
    def get_document_title_from_metadata(self) -> Optional[str]:
        """Extract title from PDF metadata."""
        if self.doc and self.doc.metadata and self.doc.metadata.get('title'):
            return self.doc.metadata['title'].strip()
        return None
    
    def get_document_info(self) -> Dict:
        """Get comprehensive document information."""
        if not self.doc:
            return {}
        
        return {
            'filename': os.path.basename(self.pdf_path),
            'file_size_mb': round(os.path.getsize(self.pdf_path) / (1024 * 1024), 2),
            'metadata': self.metadata,
            'page_count': self.doc.page_count,
            'is_encrypted': self.doc.is_encrypted,
            'has_text': self._has_extractable_text(),
            'estimated_words': self._estimate_word_count()
        }
    
    def extract_text_spans_with_properties(self) -> List[Dict]:
        """
        Extracts all text spans from the PDF with detailed properties.
        Returns a list of dictionaries, each representing a text span.
        """
        if not self.doc:
            logging.error("PDF not open. Call open_pdf() first.")
            return []

        all_spans_data = []
        total_spans = 0
        
        try:
            for page_num in range(self.doc.page_count):
                page = self.doc[page_num]
                page_dict = page.get_text("dict")  # Get text in dictionary format
                page_width = page.rect.width
                page_height = page.rect.height

                page_spans = 0
                for block in page_dict.get('blocks', []):
                    if block.get('type') == 0:  # 0 means it's a text block
                        for line in block.get('lines', []):
                            for span in line.get('spans', []):
                                # Basic cleaning: remove extra whitespace
                                text = span.get('text', '').strip()
                                if not text:  # Skip empty spans
                                    continue

                                # Validate span data
                                bbox = span.get('bbox', [0, 0, 0, 0])
                                if len(bbox) != 4:
                                    continue

                                span_data = {
                                    'text': text,
                                    'page_num': page_num + 1,  # 1-indexed page number
                                    'x0': float(bbox[0]),
                                    'y0': float(bbox[1]),
                                    'x1': float(bbox[2]),
                                    'y1': float(bbox[3]),
                                    'font_name': span.get('font', 'Unknown'),
                                    'font_size': float(span.get('size', 12)),
                                    'is_bold': bool(span.get('flags', 0) & 0x04),  # Bit 2 (0x04) for bold
                                    'is_italic': bool(span.get('flags', 0) & 0x02),  # Bit 1 (0x02) for italic
                                    'color': span.get('color', 0),  # Integer hex color
                                    'page_width': float(page_width),
                                    'page_height': float(page_height),
                                    # Additional computed properties
                                    'width': float(bbox[2] - bbox[0]),
                                    'height': float(bbox[3] - bbox[1]),
                                    'x_center': float((bbox[0] + bbox[2]) / 2),
                                    'y_center': float((bbox[1] + bbox[3]) / 2),
                                    # Relative positions (0-1 scale)
                                    'x0_rel': float(bbox[0] / page_width) if page_width > 0 else 0,
                                    'y0_rel': float(bbox[1] / page_height) if page_height > 0 else 0,
                                    'x1_rel': float(bbox[2] / page_width) if page_width > 0 else 0,
                                    'y1_rel': float(bbox[3] / page_height) if page_height > 0 else 0,
                                    'width_rel': float((bbox[2] - bbox[0]) / page_width) if page_width > 0 else 0,
                                    'height_rel': float((bbox[3] - bbox[1]) / page_height) if page_height > 0 else 0,
                                    # Text properties
                                    'char_count': len(text),
                                    'word_count': len(text.split()),
                                    'is_numeric': text.replace('.', '').replace(',', '').isdigit(),
                                    'is_uppercase': text.isupper(),
                                    'starts_with_number': text[0].isdigit() if text else False,
                                    'ends_with_punctuation': text[-1] in '.!?:;' if text else False
                                }
                                
                                all_spans_data.append(span_data)
                                page_spans += 1
                                total_spans += 1
                
                logging.debug(f"Page {page_num + 1}: extracted {page_spans} spans")
                
        except Exception as e:
            logging.error(f"Error extracting text spans: {e}")
            return []
        
        logging.info(f"Extracted {total_spans} text spans from {self.doc.page_count} pages")
        return all_spans_data
    
    def extract_text_by_page(self) -> List[Dict]:
        """Extract text content organized by page."""
        if not self.doc:
            logging.error("PDF not open. Call open_pdf() first.")
            return []
        
        pages_data = []
        
        try:
            for page_num in range(self.doc.page_count):
                page = self.doc[page_num]
                
                # Extract plain text
                text = page.get_text()
                
                # Extract text with formatting
                text_dict = page.get_text("dict")
                
                # Calculate page statistics
                word_count = len(text.split())
                char_count = len(text)
                
                page_data = {
                    'page_number': page_num + 1,
                    'text': text.strip(),
                    'word_count': word_count,
                    'char_count': char_count,
                    'width': float(page.rect.width),
                    'height': float(page.rect.height),
                    'rotation': page.rotation,
                    'has_images': len(page.get_images()) > 0,
                    'image_count': len(page.get_images()),
                    'block_count': len(text_dict.get('blocks', [])),
                    'is_empty': word_count == 0
                }
                
                pages_data.append(page_data)
                
        except Exception as e:
            logging.error(f"Error extracting text by page: {e}")
            return []
        
        return pages_data
    
    def extract_images_info(self) -> List[Dict]:
        """Extract information about images in the PDF."""
        if not self.doc:
            logging.error("PDF not open. Call open_pdf() first.")
            return []
        
        images_info = []
        
        try:
            for page_num in range(self.doc.page_count):
                page = self.doc[page_num]
                image_list = page.get_images()
                
                for img_index, img in enumerate(image_list):
                    try:
                        # Get image properties
                        xref = img[0]
                        pix = fitz.Pixmap(self.doc, xref)
                        
                        image_info = {
                            'page_number': page_num + 1,
                            'image_index': img_index,
                            'xref': xref,
                            'width': pix.width,
                            'height': pix.height,
                            'colorspace': pix.colorspace.name if pix.colorspace else 'Unknown',
                            'bits_per_component': pix.n,
                            'size_bytes': len(pix.tobytes())
                        }
                        
                        images_info.append(image_info)
                        pix = None  # Clean up
                        
                    except Exception as e:
                        logging.warning(f"Error processing image {img_index} on page {page_num + 1}: {e}")
                        continue
                        
        except Exception as e:
            logging.error(f"Error extracting image information: {e}")
            return []
        
        return images_info
    
    def get_page_layout_analysis(self, page_num: int = 0) -> Dict:
        """Analyze layout structure of a specific page."""
        if not self.doc or page_num >= self.doc.page_count:
            return {}
        
        try:
            page = self.doc[page_num]
            page_dict = page.get_text("dict")
            
            # Analyze text blocks
            text_blocks = []
            for block in page_dict.get('blocks', []):
                if block.get('type') == 0:  # Text block
                    bbox = block.get('bbox', [0, 0, 0, 0])
                    text_content = ""
                    
                    for line in block.get('lines', []):
                        for span in line.get('spans', []):
                            text_content += span.get('text', '') + " "
                    
                    text_blocks.append({
                        'bbox': bbox,
                        'text': text_content.strip(),
                        'word_count': len(text_content.split()),
                        'area': (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])
                    })
            
            # Calculate layout metrics
            page_area = page.rect.width * page.rect.height
            text_coverage = sum(block['area'] for block in text_blocks) / page_area if page_area > 0 else 0
            
            return {
                'page_number': page_num + 1,
                'page_width': float(page.rect.width),
                'page_height': float(page.rect.height),
                'text_blocks_count': len(text_blocks),
                'text_coverage_ratio': text_coverage,
                'has_multiple_columns': self._detect_columns(text_blocks),
                'text_blocks': text_blocks[:10]  # Limit for output size
            }
            
        except Exception as e:
            logging.error(f"Error analyzing page layout: {e}")
            return {}
    
    def _has_extractable_text(self) -> bool:
        """Check if PDF has extractable text."""
        if not self.doc:
            return False
        
        try:
            # Check first few pages for text
            for page_num in range(min(3, self.doc.page_count)):
                page = self.doc[page_num]
                text = page.get_text().strip()
                if text and len(text) > 10:
                    return True
            return False
        except:
            return False
    
    def _estimate_word_count(self) -> int:
        """Estimate total word count in document."""
        if not self.doc:
            return 0
        
        try:
            total_words = 0
            # Sample first 5 pages to estimate
            sample_pages = min(5, self.doc.page_count)
            
            for page_num in range(sample_pages):
                page = self.doc[page_num]
                text = page.get_text()
                total_words += len(text.split())
            
            # Extrapolate to full document
            if sample_pages > 0:
                avg_words_per_page = total_words / sample_pages
                return int(avg_words_per_page * self.doc.page_count)
            
            return 0
            
        except:
            return 0
    
    def _detect_columns(self, text_blocks: List[Dict]) -> bool:
        """Simple column detection based on text block positions."""
        if len(text_blocks) < 2:
            return False
        
        try:
            # Group blocks by approximate x-position
            left_blocks = []
            right_blocks = []
            
            # Find page center
            if text_blocks:
                page_width = max(block['bbox'][2] for block in text_blocks)
                center_x = page_width / 2
                
                for block in text_blocks:
                    block_center_x = (block['bbox'][0] + block['bbox'][2]) / 2
                    if block_center_x < center_x:
                        left_blocks.append(block)
                    else:
                        right_blocks.append(block)
                
                # If we have significant blocks on both sides, likely multi-column
                return len(left_blocks) > 0 and len(right_blocks) > 0 and \
                       min(len(left_blocks), len(right_blocks)) >= len(text_blocks) * 0.3
            
            return False
            
        except:
            return False
    
    def save_spans_to_csv(self, output_path: str) -> bool:
        """Save extracted spans to CSV file for analysis."""
        try:
            spans_data = self.extract_text_spans_with_properties()
            if not spans_data:
                logging.warning("No spans data to save")
                return False
            
            df = pd.DataFrame(spans_data)
            df.to_csv(output_path, index=False, encoding='utf-8')
            logging.info(f"Saved {len(spans_data)} spans to {output_path}")
            return True
            
        except Exception as e:
            logging.error(f"Error saving spans to CSV: {e}")
            return False
    
    def __enter__(self):
        """Context manager entry."""
        if self.open_pdf():
            return self
        else:
            raise Exception(f"Failed to open PDF: {self.pdf_path}")
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close_pdf()
    
    def __del__(self):
        """Destructor to ensure PDF is closed."""
        self.close_pdf()
