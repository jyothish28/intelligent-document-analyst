# src/main.py
import os
import json
import time
import logging
from datetime import datetime
from src.document_processor import DocumentProcessor
from src.content_analyzer import ContentAnalyzer
from src.persona_matcher import PersonaMatcher
from src.section_prioritizer import SectionPrioritizer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('/app/output/processing.log')
    ]
)

def load_config():
    """Load challenge configuration with validation."""
    config_path = "/app/input/config.json"
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # Validate required fields
        required_fields = ['persona', 'job_to_be_done']
        for field in required_fields:
            if field not in config:
                logging.error(f"Missing required field: {field}")
                return None
        
        logging.info("Configuration loaded successfully")
        return config
        
    except FileNotFoundError:
        logging.error(f"Config file not found at {config_path}")
        return None
    except json.JSONDecodeError as e:
        logging.error(f"Error parsing config JSON: {e}")
        return None
    except Exception as e:
        logging.error(f"Unexpected error loading config: {e}")
        return None

def get_pdf_files(config):
    """Get list of PDF files with validation."""
    docs_dir = "/app/input/documents"
    
    # Check if documents are specified in config
    if config and 'documents' in config:
        pdf_files = []
        for doc in config['documents']:
            filename = doc['filename']
            pdf_path = os.path.join(docs_dir, filename)
            if os.path.exists(pdf_path):
                pdf_files.append(pdf_path)
                logging.info(f"Found document: {filename}")
            else:
                logging.warning(f"Document {filename} not found in {docs_dir}")
        return pdf_files
    
    # Fallback: scan documents directory
    if not os.path.exists(docs_dir):
        logging.error(f"Documents directory not found: {docs_dir}")
        return []
    
    pdf_files = []
    for file in os.listdir(docs_dir):
        if file.lower().endswith('.pdf'):
            pdf_path = os.path.join(docs_dir, file)
            pdf_files.append(pdf_path)
            logging.info(f"Found PDF file: {file}")
    
    return pdf_files

def validate_output(result):
    """Validate output structure."""
    required_keys = ['metadata', 'extracted_sections', 'subsection_analysis']
    for key in required_keys:
        if key not in result:
            logging.error(f"Missing required output key: {key}")
            return False
    
    if not isinstance(result['extracted_sections'], list):
        logging.error("extracted_sections must be a list")
        return False
    
    if not isinstance(result['subsection_analysis'], list):
        logging.error("subsection_analysis must be a list")
        return False
    
    return True

def main():
    start_time = time.time()
    
    logging.info("Starting Intelligent Document Analysis...")
    
    try:
        # Load configuration
        config = load_config()
        if not config:
            logging.error("Failed to load configuration. Exiting.")
            return 1
        
        # Extract persona and job from config
        persona = config.get('persona', {})
        job_to_be_done_obj = config.get('job_to_be_done', {})
        
        # Handle both string and object formats for job_to_be_done
        if isinstance(job_to_be_done_obj, dict):
            job_to_be_done = job_to_be_done_obj.get('task', '')
        else:
            job_to_be_done = str(job_to_be_done_obj)
        
        logging.info(f"Persona: {persona.get('role', 'Unknown')}")
        logging.info(f"Job: {job_to_be_done}")
        
        # Get PDF files
        pdf_files = get_pdf_files(config)
        if not pdf_files:
            logging.error("No PDF files found. Exiting.")
            return 1
        
        logging.info(f"Found {len(pdf_files)} PDF files to process")
        
        # Initialize components
        doc_processor = DocumentProcessor()
        content_analyzer = ContentAnalyzer()
        persona_matcher = PersonaMatcher(persona, job_to_be_done)
        section_prioritizer = SectionPrioritizer()
        
        # Process documents
        all_sections = []
        document_metadata = []
        
        for pdf_path in pdf_files:
            logging.info(f"Processing: {os.path.basename(pdf_path)}")
            
            try:
                # Extract sections from document
                sections = doc_processor.extract_sections(pdf_path)
                if sections:
                    all_sections.extend(sections)
                    document_metadata.append({
                        "filename": os.path.basename(pdf_path),
                        "path": pdf_path,
                        "sections_count": len(sections)
                    })
                    logging.info(f"Extracted {len(sections)} sections from {os.path.basename(pdf_path)}")
                else:
                    logging.warning(f"No sections extracted from {os.path.basename(pdf_path)}")
                    
            except Exception as e:
                logging.error(f"Error processing {os.path.basename(pdf_path)}: {e}")
                continue
        
        if not all_sections:
            logging.error("No sections extracted from any documents. Exiting.")
            return 1
        
        logging.info(f"Extracted {len(all_sections)} sections total")
        
        # Analyze content relevance
        logging.info("Analyzing content relevance...")
        try:
            analyzed_sections = content_analyzer.analyze_sections(all_sections, persona, job_to_be_done)
        except Exception as e:
            logging.error(f"Error in content analysis: {e}")
            return 1
        
        # Match to persona and job
        logging.info("Matching to persona requirements...")
        try:
            matched_sections = persona_matcher.score_sections(analyzed_sections)
        except Exception as e:
            logging.error(f"Error in persona matching: {e}")
            return 1
        
        # Prioritize sections
        logging.info("Prioritizing sections...")
        try:
            prioritized_sections = section_prioritizer.rank_sections(matched_sections)
        except Exception as e:
            logging.error(f"Error in section prioritization: {e}")
            return 1
        
        # Generate output in expected format
        result = {
            "metadata": {
                "input_documents": [doc["filename"] for doc in document_metadata],
                "persona": persona.get('role', 'Unknown'),
                "job_to_be_done": job_to_be_done,
                "processing_timestamp": datetime.now().isoformat(),
                "total_sections_analyzed": len(all_sections),
                "processing_time_seconds": round(time.time() - start_time, 2),
                "top_sections_count": min(20, len(prioritized_sections)),
                "subsections_count": min(20, len(prioritized_sections[:10]))
            },
            "extracted_sections": [
                {
                    "document": section["document"],
                    "section_title": section["section_title"],
                    "importance_rank": section["rank"],
                    "page_number": section["page_number"],
                    "final_score": section.get("final_score", 0),
                    "priority_category": section.get("priority_category", "medium")
                }
                for section in prioritized_sections[:20]
            ],
            "subsection_analysis": section_prioritizer.get_subsection_analysis(prioritized_sections[:10])
        }
        
        # Validate output
        if not validate_output(result):
            logging.error("Output validation failed")
            return 1
        
        # Save result
        output_path = "/app/output/analysis_result.json"
        try:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            
            logging.info(f"Analysis complete! Results saved to {output_path}")
            logging.info(f"Processing time: {result['metadata']['processing_time_seconds']} seconds")
            logging.info(f"Top sections: {len(result['extracted_sections'])}")
            logging.info(f"Subsections: {len(result['subsection_analysis'])}")
            
            return 0
            
        except Exception as e:
            logging.error(f"Error saving results: {e}")
            return 1
            
    except Exception as e:
        logging.error(f"Unexpected error in main: {e}")
        return 1

if __name__ == "__main__":
    exit_code = main()
    exit(exit_code)

