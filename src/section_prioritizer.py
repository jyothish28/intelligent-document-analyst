# src/section_prioritizer.py
import re
from typing import List, Dict
import logging

class SectionPrioritizer:
    def __init__(self):
        self.priority_keywords = {
            'high': ['conclusion', 'summary', 'key findings', 'results', 'important'],
            'medium': ['methodology', 'approach', 'analysis', 'discussion'],
            'low': ['introduction', 'background', 'literature', 'references']
        }
    
    def rank_sections(self, sections: List[Dict]) -> List[Dict]:
        """Rank sections by importance with enhanced logic."""
        if not sections:
            return []
        
        # Add ranking factors
        for section in sections:
            section['final_score'] = self._calculate_final_score(section)
            section['priority_category'] = self._determine_priority_category(section)
        
        # Sort by final score (descending)
        ranked_sections = sorted(sections, key=lambda x: x['final_score'], reverse=True)
        
        # Assign ranks with tie handling
        current_rank = 1
        for i, section in enumerate(ranked_sections):
            if i > 0 and ranked_sections[i-1]['final_score'] != section['final_score']:
                current_rank = i + 1
            section['rank'] = current_rank
        
        logging.info(f"Ranked {len(ranked_sections)} sections")
        return ranked_sections
    
    def _calculate_final_score(self, section: Dict) -> float:
        """Calculate final ranking score with multiple factors."""
        base_score = section.get('importance_rank', 0)
        
        # Heading level bonus (higher level = more important)
        heading_level = section.get('heading_level', 4)
        level_bonus = max(0, 5 - heading_level)  # Level 1 gets 4 points, Level 4 gets 1
        
        # Content length factor (optimal range)
        content_length = len(section.get('content', '').split())
        if 50 <= content_length <= 300:
            length_bonus = 2.0
        elif 30 <= content_length < 50 or 300 < content_length <= 500:
            length_bonus = 1.0
        else:
            length_bonus = 0.0
        
        # Title quality bonus
        title_bonus = self._assess_title_quality(section.get('section_title', ''))
        
        # Position bonus (earlier sections often more important)
        page_number = section.get('page_number', 999)
        position_bonus = max(0, 3 - (page_number - 1) * 0.1)
        
        # Key terms quality bonus
        key_terms = section.get('key_terms', [])
        if isinstance(key_terms, list) and key_terms:
            if isinstance(key_terms[0], dict):
                terms_bonus = sum(term.get('score', 0) for term in key_terms[:3])
            else:
                terms_bonus = len(key_terms) * 0.5
        else:
            terms_bonus = 0
        
        final_score = (base_score + level_bonus + length_bonus + 
                      title_bonus + position_bonus + terms_bonus)
        
        return round(final_score, 2)
    
    def _assess_title_quality(self, title: str) -> float:
        """Assess the quality and informativeness of section title."""
        if not title or len(title) < 3:
            return 0.0
        
        score = 0.0
        title_lower = title.lower()
        
        # Length factor
        if 5 <= len(title.split()) <= 10:
            score += 1.0
        elif 3 <= len(title.split()) <= 15:
            score += 0.5
        
        # Informativeness indicators
        informative_words = [
            'analysis', 'method', 'result', 'conclusion', 'finding',
            'approach', 'technique', 'process', 'evaluation', 'comparison'
        ]
        score += sum(0.5 for word in informative_words if word in title_lower)
        
        # Priority keywords
        for priority, keywords in self.priority_keywords.items():
            for keyword in keywords:
                if keyword in title_lower:
                    if priority == 'high':
                        score += 2.0
                    elif priority == 'medium':
                        score += 1.0
                    else:
                        score += 0.5
        
        return min(score, 5.0)
    
    def _determine_priority_category(self, section: Dict) -> str:
        """Determine priority category for section."""
        title = section.get('section_title', '').lower()
        score = section.get('final_score', 0)
        
        # High priority indicators
        if (score > 15 or 
            any(keyword in title for keyword in self.priority_keywords['high'])):
            return 'high'
        
        # Low priority indicators
        elif (score < 5 or 
              any(keyword in title for keyword in self.priority_keywords['low'])):
            return 'low'
        
        # Medium priority (default)
        else:
            return 'medium'
    
    def get_subsection_analysis(self, top_sections: List[Dict]) -> List[Dict]:
        """Generate enhanced sub-section analysis."""
        subsection_analysis = []
        
        for section in top_sections:
            # Split content into meaningful subsections
            subsections = self._split_into_smart_subsections(section['content'])
            
            for i, subsection_text in enumerate(subsections):
                if len(subsection_text.strip()) > 30:  # Only meaningful subsections
                    refined_text = self._refine_text_advanced(subsection_text)
                    
                    # Calculate subsection relevance
                    relevance = self._calculate_subsection_relevance(
                        subsection_text, section
                    )
                    
                    subsection_analysis.append({
                        "document": section['document'],
                        "page_number": section['page_number'],
                        "subsection_id": f"{section['rank']}.{i+1}",
                        "refined_text": refined_text,
                        "parent_section": section['section_title'],
                        "relevance_score": relevance,
                        "word_count": len(refined_text.split()),
                        "key_concepts": self._extract_key_concepts(subsection_text)
                    })
        
        # Sort by relevance and return top subsections
        subsection_analysis.sort(key=lambda x: x['relevance_score'], reverse=True)
        return subsection_analysis[:20]  # Top 20 subsections
    
    def _split_into_smart_subsections(self, content: str) -> List[str]:
        """Smart subsection splitting based on content structure."""
        if not content or len(content.strip()) < 50:
            return [content]
        
        # Try to split by natural breaks
        subsections = []
        
        # First, try splitting by paragraph breaks or double newlines
        paragraphs = re.split(r'\n\s*\n|\.\s{2,}', content)
        
        current_subsection = ""
        target_length = 150  # Target words per subsection
        
        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if not paragraph:
                continue
            
            # If adding this paragraph would make subsection too long, start new one
            if (len(current_subsection.split()) + len(paragraph.split()) > target_length * 1.5 
                and len(current_subsection.split()) > target_length * 0.5):
                
                if current_subsection.strip():
                    subsections.append(current_subsection.strip())
                current_subsection = paragraph
            else:
                current_subsection += " " + paragraph if current_subsection else paragraph
        
        # Add remaining content
        if current_subsection.strip():
            subsections.append(current_subsection.strip())
        
        # If no natural breaks found, split by sentences
        if len(subsections) <= 1 and len(content.split()) > target_length:
            return self._split_by_sentences(content, target_length)
        
        return subsections
    
    def _split_by_sentences(self, content: str, target_length: int) -> List[str]:
        """Split content by sentences when no natural breaks exist."""
        sentences = re.split(r'[.!?]+', content)
        subsections = []
        current_subsection = ""
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            sentence += "."  # Add back the period
            
            if (len(current_subsection.split()) + len(sentence.split()) > target_length 
                and len(current_subsection.split()) > target_length * 0.3):
                
                if current_subsection.strip():
                    subsections.append(current_subsection.strip())
                current_subsection = sentence
            else:
                current_subsection += " " + sentence if current_subsection else sentence
        
        if current_subsection.strip():
            subsections.append(current_subsection.strip())
        
        return subsections
    
    def _refine_text_advanced(self, text: str) -> str:
        """Advanced text refinement for better readability."""
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Fix sentence boundaries
        text = re.sub(r'([a-z])([A-Z])', r'\1. \2', text)
        
        # Clean up common OCR errors
        text = text.replace('  ', ' ')
        text = text.replace(' .', '.')
        text = text.replace(' ,', ',')
        text = text.replace('( ', '(')
        text = text.replace(' )', ')')
        
        # Ensure proper sentence endings
        if text and not text.endswith(('.', '!', '?')):
            text += '.'
        
        # Limit length for readability
        words = text.split()
        if len(words) > 120:
            # Try to cut at a sentence boundary
            sentences = re.split(r'[.!?]+', text)
            truncated = ""
            word_count = 0
            
            for sentence in sentences:
                sentence_words = len(sentence.split())
                if word_count + sentence_words <= 120:
                    truncated += sentence + ". "
                    word_count += sentence_words
                else:
                    break
            
            if truncated:
                text = truncated.strip()
            else:
                text = ' '.join(words[:120]) + '...'
        
        return text.strip()
    
    def _calculate_subsection_relevance(self, subsection_text: str, parent_section: Dict) -> float:
        """Calculate relevance score for a subsection."""
        base_score = parent_section.get('importance_rank', 0) * 0.7
        
        # Content quality factors
        word_count = len(subsection_text.split())
        if 30 <= word_count <= 150:
            length_bonus = 2.0
        elif 20 <= word_count < 30 or 150 < word_count <= 200:
            length_bonus = 1.0
        else:
            length_bonus = 0.0
        
        # Information density
        unique_words = len(set(subsection_text.lower().split()))
        total_words = len(subsection_text.split())
        density_score = (unique_words / total_words) * 2 if total_words > 0 else 0
        
        # Key term presence
        parent_key_terms = parent_section.get('key_terms', [])
        if isinstance(parent_key_terms, list) and parent_key_terms:
            if isinstance(parent_key_terms[0], dict):
                key_terms = [term['term'] for term in parent_key_terms]
            else:
                key_terms = parent_key_terms
            
            term_matches = sum(1 for term in key_terms if term in subsection_text.lower())
            term_bonus = min(term_matches * 0.5, 3.0)
        else:
            term_bonus = 0
        
        total_score = base_score + length_bonus + density_score + term_bonus
        return round(total_score, 2)
    
    def _extract_key_concepts(self, text: str) -> List[str]:
        """Extract key concepts from subsection text."""
        # Simple concept extraction based on capitalized terms and important words
        concepts = []
        
        # Find capitalized terms (potential proper nouns/concepts)
        capitalized_terms = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', text)
        concepts.extend(capitalized_terms[:3])
        
        # Find important technical terms
        important_patterns = [
            r'\b\w*(?:tion|sion|ment|ness|ity|ism)\b',  # Abstract nouns
            r'\b\w{8,}\b',  # Long words (often technical)
        ]
        
        for pattern in important_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            concepts.extend(matches[:2])
        
        # Remove duplicates and return top concepts
        unique_concepts = list(dict.fromkeys(concepts))  # Preserve order
        return unique_concepts[:5]
