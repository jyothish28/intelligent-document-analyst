# src/config_manager.py
import os
import json
import logging
from typing import Dict, List, Optional
from datetime import datetime

class ConfigManager:
    def __init__(self, input_dir: str = "/app/input", output_dir: str = "/app/output"):
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.config_path = os.path.join(input_dir, "config.json")
        self.documents_dir = os.path.join(input_dir, "documents")
        
    def load_and_enhance_config(self) -> Optional[Dict]:
        """Load config and enhance with auto-detected files."""
        try:
            # Load base config
            base_config = self._load_base_config()
            if not base_config:
                return None
            
            # Auto-detect and add PDF files
            enhanced_config = self._enhance_with_pdf_detection(base_config)
            
            # Add metadata
            enhanced_config['config_metadata'] = {
                'loaded_at': datetime.now().isoformat(),
                'auto_enhanced': True,
                'input_directory': self.input_dir,
                'documents_directory': self.documents_dir
            }
            
            # Save enhanced config
            self._save_enhanced_config(enhanced_config)
            
            return enhanced_config
            
        except Exception as e:
            logging.error(f"Error loading and enhancing config: {e}")
            return None
    
    def _load_base_config(self) -> Optional[Dict]:
        """Load the base configuration file."""
        if not os.path.exists(self.config_path):
            # Create minimal config if none exists
            logging.warning(f"Config file not found. Creating minimal config at {self.config_path}")
            return self._create_minimal_config()
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # Validate required fields
            required_fields = ['persona', 'job_to_be_done']
            for field in required_fields:
                if field not in config:
                    logging.error(f"Missing required field: {field}")
                    return None
            
            logging.info("Base configuration loaded successfully")
            return config
            
        except json.JSONDecodeError as e:
            logging.error(f"Error parsing config JSON: {e}")
            return None
        except Exception as e:
            logging.error(f"Unexpected error loading config: {e}")
            return None
    
    def _create_minimal_config(self) -> Dict:
        """Create a minimal configuration with defaults."""
        minimal_config = {
            "persona": {
                "role": "Analyst",
                "expertise": ["document analysis", "information extraction"],
                "experience_level": "intermediate"
            },
            "job_to_be_done": {
                "task": "Extract and analyze key information from documents",
                "priority": "high",
                "focus_areas": ["main concepts", "important findings", "methodologies"]
            },
            "processing_options": {
                "max_sections": 20,
                "min_section_length": 50,
                "include_subsections": True
            }
        }
        
        # Save minimal config
        try:
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(minimal_config, f, indent=2, ensure_ascii=False)
            logging.info(f"Created minimal config at {self.config_path}")
        except Exception as e:
            logging.warning(f"Could not save minimal config: {e}")
        
        return minimal_config
    
    def _enhance_with_pdf_detection(self, base_config: Dict) -> Dict:
        """Enhance config with auto-detected PDF files."""
        enhanced_config = base_config.copy()
        
        # Auto-detect PDF files
        detected_pdfs = self._scan_for_pdfs()
        
        if detected_pdfs:
            enhanced_config['documents'] = detected_pdfs
            enhanced_config['auto_detected_pdfs'] = True
            enhanced_config['total_pdfs_found'] = len(detected_pdfs)
            
            logging.info(f"Auto-detected {len(detected_pdfs)} PDF files")
            for pdf in detected_pdfs:
                logging.info(f"  - {pdf['filename']} ({pdf['size_mb']} MB)")
        else:
            enhanced_config['documents'] = []
            enhanced_config['auto_detected_pdfs'] = False
            enhanced_config['total_pdfs_found'] = 0
            logging.warning("No PDF files found in documents directory")
        
        return enhanced_config
    
    def _scan_for_pdfs(self) -> List[Dict]:
        """Scan documents directory for PDF files."""
        if not os.path.exists(self.documents_dir):
            logging.warning(f"Documents directory not found: {self.documents_dir}")
            return []
        
        detected_pdfs = []
        
        try:
            for file in sorted(os.listdir(self.documents_dir)):
                if file.lower().endswith('.pdf'):
                    pdf_path = os.path.join(self.documents_dir, file)
                    
                    if os.path.exists(pdf_path):
                        file_stats = os.stat(pdf_path)
                        
                        pdf_info = {
                            "filename": file,
                            "path": pdf_path,
                            "size_bytes": file_stats.st_size,
                            "size_mb": round(file_stats.st_size / (1024 * 1024), 2),
                            "modified_date": datetime.fromtimestamp(file_stats.st_mtime).isoformat(),
                            "detected_at": datetime.now().isoformat()
                        }
                        
                        detected_pdfs.append(pdf_info)
                        
        except Exception as e:
            logging.error(f"Error scanning for PDFs: {e}")
            return []
        
        return detected_pdfs
    
    def _save_enhanced_config(self, enhanced_config: Dict) -> None:
        """Save the enhanced configuration for reference."""
        try:
            enhanced_config_path = os.path.join(self.output_dir, "enhanced_config.json")
            os.makedirs(self.output_dir, exist_ok=True)
            
            with open(enhanced_config_path, 'w', encoding='utf-8') as f:
                json.dump(enhanced_config, f, indent=2, ensure_ascii=False)
            
            logging.info(f"Enhanced config saved to: {enhanced_config_path}")
            
        except Exception as e:
            logging.warning(f"Could not save enhanced config: {e}")
    
    def get_pdf_files(self, config: Dict) -> List[str]:
        """Extract PDF file paths from config."""
        pdf_files = []
        
        if not config or 'documents' not in config:
            return pdf_files
        
        for doc in config['documents']:
            if isinstance(doc, dict):
                pdf_path = doc.get('path', '')
                filename = doc.get('filename', '')
                
                if pdf_path and os.path.exists(pdf_path):
                    pdf_files.append(pdf_path)
                elif filename:
                    # Fallback to constructing path
                    fallback_path = os.path.join(self.documents_dir, filename)
                    if os.path.exists(fallback_path):
                        pdf_files.append(fallback_path)
                        
        return pdf_files
    
    def validate_config(self, config: Dict) -> bool:
        """Validate configuration structure."""
        required_fields = ['persona', 'job_to_be_done']
        
        for field in required_fields:
            if field not in config:
                logging.error(f"Missing required field: {field}")
                return False
        
        # Validate persona structure
        persona = config.get('persona', {})
        if not isinstance(persona, dict) or 'role' not in persona:
            logging.error("Invalid persona structure - must have 'role' field")
            return False
        
        # Validate job_to_be_done
        job = config.get('job_to_be_done', {})
        if isinstance(job, dict):
            if 'task' not in job:
                logging.error("Invalid job_to_be_done structure - must have 'task' field")
                return False
        elif not isinstance(job, str):
            logging.error("job_to_be_done must be string or object with 'task' field")
            return False
        
        return True