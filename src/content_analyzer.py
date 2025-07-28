# src/content_analyzer.py
import re
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from typing import List, Dict, Set
import logging

class ContentAnalyzer:
    def __init__(self):
        self.vectorizer = TfidfVectorizer(
            max_features=2000,
            stop_words='english',
            ngram_range=(1, 3),
            min_df=1,
            max_df=0.95,
            lowercase=True,
            token_pattern=r'\b[a-zA-Z][a-zA-Z0-9]*\b'
        )
        
        # Domain-specific keywords for different fields
        self.domain_keywords = {
            'computer_science': ['algorithm', 'data structure', 'programming', 'software', 'database', 'network'],
            'machine_learning': ['model', 'training', 'neural', 'classification', 'regression', 'feature'],
            'research': ['methodology', 'experiment', 'hypothesis', 'analysis', 'findings', 'literature'],
            'business': ['strategy', 'market', 'revenue', 'customer', 'profit', 'analysis'],
            'education': ['learning', 'concept', 'theory', 'principle', 'example', 'definition']
        }
        
    def analyze_sections(self, sections: List[Dict], persona: Dict, job: str) -> List[Dict]:
        """Analyze sections with enhanced relevance scoring."""
        if not sections:
            return []
        
        logging.info(f"Analyzing {len(sections)} sections for relevance")
        
        # Prepare texts for analysis
        section_texts = []
        for section in sections:
            combined_text = f"{section['section_title']} {section['content']}"
            cleaned_text = self._advanced_text_cleaning(combined_text)
            section_texts.append(cleaned_text)
        
        # Create TF-IDF vectors with error handling
        try:
            if len(section_texts) == 1:
                # Handle single document case
                tfidf_matrix = self.vectorizer.fit_transform(section_texts + ["dummy text"])
                tfidf_matrix = tfidf_matrix[:1]  # Keep only the real document
            else:
                tfidf_matrix = self.vectorizer.fit_transform(section_texts)
        except ValueError as e:
            logging.warning(f"TF-IDF failed: {e}. Using fallback analysis.")
            return self._fallback_analysis(sections, persona, job)
        
        # Analyze each section
        analyzed_sections = []
        for i, section in enumerate(sections):
            analysis = section.copy()
            
            # Calculate multiple relevance scores
            analysis['relevance_score'] = self._calculate_enhanced_relevance(
                section_texts[i], section, persona, job
            )
            
            # Extract key terms with confidence scores
            analysis['key_terms'] = self._extract_enhanced_key_terms(
                tfidf_matrix[i], section_texts[i]
            )
            
            # Content quality with multiple metrics
            analysis['content_quality'] = self._assess_enhanced_content_quality(section)
            
            # Domain relevance
            analysis['domain_relevance'] = self._calculate_domain_relevance(
                section_texts[i], persona, job
            )
            
            # Semantic density
            analysis['semantic_density'] = self._calculate_semantic_density(section_texts[i])
            
            analyzed_sections.append(analysis)
        
        return analyzed_sections
    
    def _advanced_text_cleaning(self, text: str) -> str:
        """Advanced text cleaning and normalization."""
        # Remove extra whitespace and normalize
        text = re.sub(r'\s+', ' ', text)
        
        # Remove special characters but keep important punctuation
        text = re.sub(r'[^\w\s.,;:!?()-]', ' ', text)
        
        # Fix common OCR errors
        text = re.sub(r'\b(\w)\1{3,}\b', r'\1', text)  # Remove repeated characters
        text = re.sub(r'\b[a-z]\b', '', text)  # Remove single letters
        
        # Normalize case
        text = text.lower().strip()
        
        return text
    
    def _calculate_enhanced_relevance(self, text: str, section: Dict, persona: Dict, job: str) -> float:
        """Enhanced relevance calculation with multiple factors."""
        score = 0.0
        
        # Job-related keywords (weighted by importance)
        job_keywords = self._extract_smart_keywords(job.lower())
        for keyword in job_keywords:
            if keyword in text:
                # Weight by keyword length and frequency
                frequency = text.count(keyword)
                weight = len(keyword.split()) * frequency
                score += min(weight * 2.0, 8.0)  # Cap individual keyword contribution
        
        # Persona expertise matching
        expertise = persona.get('expertise', [])
        for area in expertise:
            area_lower = area.lower()
            if area_lower in text:
                score += 3.0
            # Partial matching for compound terms
            area_words = area_lower.split()
            if len(area_words) > 1:
                matches = sum(1 for word in area_words if word in text)
                score += (matches / len(area_words)) * 2.0
        
        # Role-specific scoring with more nuance
        role = persona.get('role', '').lower()
        role_scores = {
            'researcher': self._score_research_content(text),
            'student': self._score_educational_content(text),
            'analyst': self._score_analytical_content(text),
            'developer': self._score_technical_content(text),
            'manager': self._score_strategic_content(text)
        }
        
        for role_type, role_score in role_scores.items():
            if role_type in role:
                score += role_score
        
        # Section structure bonus
        if section.get('heading_level', 4) <= 2:
            score += 1.0  # Bonus for main sections
        
        return min(score, 20.0)  # Cap at 20
    
    def _extract_smart_keywords(self, text: str) -> List[str]:
        """Extract meaningful keywords with better filtering."""
        words = re.findall(r'\b[a-zA-Z]{3,}\b', text)
        
        # Filter out common words and keep meaningful terms
        stop_words = {'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can', 'had', 'her', 'was', 'one', 'our', 'out', 'day', 'get', 'has', 'him', 'his', 'how', 'its', 'may', 'new', 'now', 'old', 'see', 'two', 'who', 'boy', 'did', 'she', 'use', 'her', 'way', 'many', 'then', 'them', 'well', 'were'}
        
        keywords = []
        for word in words:
            if (len(word) > 3 and 
                word.lower() not in stop_words and 
                not word.isdigit()):
                keywords.append(word.lower())
        
        # Return unique keywords, prioritizing longer ones
        unique_keywords = list(set(keywords))
        unique_keywords.sort(key=len, reverse=True)
        
        return unique_keywords[:15]
    
    def _score_research_content(self, text: str) -> float:
        """Score content for research relevance."""
        research_terms = [
            'methodology', 'experiment', 'analysis', 'study', 'research',
            'hypothesis', 'findings', 'results', 'conclusion', 'literature',
            'survey', 'investigation', 'empirical', 'theoretical', 'framework'
        ]
        return sum(2.0 for term in research_terms if term in text)
    
    def _score_educational_content(self, text: str) -> float:
        """Score content for educational value."""
        educational_terms = [
            'concept', 'definition', 'example', 'theory', 'principle',
            'basics', 'fundamental', 'introduction', 'overview', 'explanation',
            'tutorial', 'guide', 'learning', 'understanding', 'knowledge'
        ]
        return sum(2.0 for term in educational_terms if term in text)
    
    def _score_analytical_content(self, text: str) -> float:
        """Score content for analytical value."""
        analytical_terms = [
            'trend', 'data', 'metric', 'performance', 'comparison',
            'insight', 'pattern', 'correlation', 'statistics', 'measurement',
            'evaluation', 'assessment', 'benchmark', 'indicator', 'analysis'
        ]
        return sum(2.0 for term in analytical_terms if term in text)
    
    def _score_technical_content(self, text: str) -> float:
        """Score content for technical relevance."""
        technical_terms = [
            'implementation', 'algorithm', 'system', 'design', 'architecture',
            'development', 'programming', 'software', 'technical', 'solution',
            'method', 'approach', 'technique', 'process', 'procedure'
        ]
        return sum(2.0 for term in technical_terms if term in text)
    
    def _score_strategic_content(self, text: str) -> float:
        """Score content for strategic/management relevance."""
        strategic_terms = [
            'strategy', 'planning', 'management', 'decision', 'leadership',
            'organization', 'business', 'objective', 'goal', 'vision',
            'mission', 'policy', 'governance', 'coordination', 'direction'
        ]
        return sum(2.0 for term in strategic_terms if term in text)
    
    def _extract_enhanced_key_terms(self, tfidf_vector, text: str) -> List[Dict]:
        """Extract key terms with confidence scores."""
        try:
            feature_names = self.vectorizer.get_feature_names_out()
            tfidf_scores = tfidf_vector.toarray()[0]
            
            # Get top terms with scores
            top_indices = np.argsort(tfidf_scores)[-10:][::-1]
            key_terms = []
            
            for i in top_indices:
                if tfidf_scores[i] > 0:
                    key_terms.append({
                        'term': feature_names[i],
                        'score': round(float(tfidf_scores[i]), 3),
                        'frequency': text.count(feature_names[i])
                    })
            
            return key_terms
        except Exception as e:
            logging.warning(f"Key term extraction failed: {e}")
            return [{'term': term, 'score': 1.0, 'frequency': 1} 
                   for term in self._extract_smart_keywords(text)[:5]]
    
    def _assess_enhanced_content_quality(self, section: Dict) -> float:
        """Enhanced content quality assessment."""
        content = section['content']
        title = section['section_title']
        
        # Length factor (optimal range)
        word_count = len(content.split())
        if word_count < 20:
            length_score = word_count / 20
        elif word_count > 500:
            length_score = 2.0 - (word_count - 500) / 1000
        else:
            length_score = 1.0 + (word_count - 20) / 480  # Scale to 1-2
        
        # Structure factor
        structure_score = 1.0
        if title and len(title) > 3:
            structure_score += 0.5
        if section.get('heading_level', 4) <= 2:
            structure_score += 0.3
        
        # Information density
        unique_words = len(set(content.lower().split()))
        total_words = len(content.split())
        info_density = unique_words / max(total_words, 1) if total_words > 0 else 0
        
        # Readability (sentence structure)
        sentences = re.split(r'[.!?]+', content)
        avg_sentence_length = sum(len(s.split()) for s in sentences) / max(len(sentences), 1)
        readability_score = 1.0 if 10 <= avg_sentence_length <= 25 else 0.5
        
        total_score = (length_score + structure_score + 
                      info_density * 2 + readability_score)
        
        return min(total_score, 5.0)
    
    def _calculate_domain_relevance(self, text: str, persona: Dict, job: str) -> float:
        """Calculate domain-specific relevance."""
        score = 0.0
        
        # Check against domain keywords
        for domain, keywords in self.domain_keywords.items():
            domain_score = sum(1.0 for keyword in keywords if keyword in text)
            if domain_score > 0:
                score += domain_score * 0.5
        
        # Boost score if domain matches persona/job context
        combined_context = f"{persona.get('role', '')} {job}".lower()
        for domain in self.domain_keywords:
            if domain.replace('_', ' ') in combined_context:
                domain_keywords = self.domain_keywords[domain]
                domain_matches = sum(1.0 for keyword in domain_keywords if keyword in text)
                score += domain_matches * 1.0
        
        return min(score, 10.0)
    
    def _calculate_semantic_density(self, text: str) -> float:
        """Calculate semantic density of the text."""
        words = text.split()
        if len(words) < 10:
            return 0.5
        
        # Calculate ratio of meaningful words
        meaningful_words = [w for w in words if len(w) > 3 and w.isalpha()]
        density = len(meaningful_words) / len(words)
        
        # Bonus for technical terms and proper nouns
        technical_bonus = sum(0.1 for word in words if word[0].isupper() or len(word) > 8)
        
        return min(density + technical_bonus, 2.0)
    
    def _fallback_analysis(self, sections: List[Dict], persona: Dict, job: str) -> List[Dict]:
        """Enhanced fallback analysis when TF-IDF fails."""
        analyzed_sections = []
        for section in sections:
            analysis = section.copy()
            combined_text = f"{section['section_title']} {section['content']}"
            cleaned_text = self._advanced_text_cleaning(combined_text)
            
            analysis['relevance_score'] = self._calculate_enhanced_relevance(
                cleaned_text, section, persona, job
            )
            analysis['key_terms'] = [
                {'term': term, 'score': 1.0, 'frequency': 1} 
                for term in self._extract_smart_keywords(cleaned_text)[:5]
            ]
            analysis['content_quality'] = self._assess_enhanced_content_quality(section)
            analysis['domain_relevance'] = self._calculate_domain_relevance(
                cleaned_text, persona, job
            )
            analysis['semantic_density'] = self._calculate_semantic_density(cleaned_text)
            
            analyzed_sections.append(analysis)
        
        return analyzed_sections
