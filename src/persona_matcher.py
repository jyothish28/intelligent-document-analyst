# src/persona_matcher.py
import re
from typing import List, Dict, Set
import logging

class PersonaMatcher:
    def __init__(self, persona: Dict, job_to_be_done: str):
        self.persona = persona
        self.job_to_be_done = job_to_be_done
        self.role = persona.get('role', '').lower()
        self.expertise = [exp.lower() for exp in persona.get('expertise', [])]
        self.experience_level = persona.get('experience_level', 'intermediate').lower()
        
        # Enhanced role-specific weights
        self.role_weights = {
            'researcher': {'methodology': 3.0, 'findings': 2.5, 'analysis': 2.0},
            'student': {'concept': 2.5, 'example': 2.0, 'definition': 2.0},
            'analyst': {'data': 2.5, 'trend': 2.0, 'metric': 2.0},
            'developer': {'implementation': 2.5, 'code': 2.0, 'system': 2.0},
            'manager': {'strategy': 2.5, 'planning': 2.0, 'decision': 2.0}
        }
        
    def score_sections(self, sections: List[Dict]) -> List[Dict]:
        """Score sections with enhanced persona matching."""
        scored_sections = []
        
        # Extract job context for better matching
        job_context = self._extract_job_context(self.job_to_be_done)
        
        for section in sections:
            scored_section = section.copy()
            
            # Calculate multiple scoring dimensions
            persona_score = self._calculate_enhanced_persona_match(section)
            job_score = self._calculate_enhanced_job_match(section, job_context)
            expertise_score = self._calculate_expertise_match(section)
            experience_score = self._calculate_experience_level_match(section)
            
            # Combined importance score with weighted factors
            scored_section['importance_rank'] = self._calculate_weighted_importance(
                section.get('relevance_score', 0),
                persona_score,
                job_score,
                section.get('content_quality', 0),
                section.get('domain_relevance', 0),
                expertise_score,
                experience_score
            )
            
            # Individual scores for transparency
            scored_section['persona_match_score'] = persona_score
            scored_section['job_match_score'] = job_score
            scored_section['expertise_match_score'] = expertise_score
            scored_section['experience_match_score'] = experience_score
            
            scored_sections.append(scored_section)
        
        return scored_sections
    
    def _extract_job_context(self, job_text: str) -> Dict:
        """Extract structured context from job description."""
        job_lower = job_text.lower()
        
        # Identify job type
        job_type = 'general'
        if any(term in job_lower for term in ['research', 'study', 'investigate']):
            job_type = 'research'
        elif any(term in job_lower for term in ['learn', 'understand', 'study']):
            job_type = 'learning'
        elif any(term in job_lower for term in ['analyze', 'examine', 'evaluate']):
            job_type = 'analysis'
        elif any(term in job_lower for term in ['implement', 'develop', 'build']):
            job_type = 'development'
        elif any(term in job_lower for term in ['plan', 'strategy', 'manage']):
            job_type = 'management'
        
        # Extract key terms and objectives
        key_terms = self._extract_meaningful_terms(job_lower)
        
        # Identify urgency/priority indicators
        urgency = 'normal'
        if any(term in job_lower for term in ['urgent', 'immediate', 'asap', 'quickly']):
            urgency = 'high'
        elif any(term in job_lower for term in ['comprehensive', 'detailed', 'thorough']):
            urgency = 'detailed'
        
        return {
            'type': job_type,
            'key_terms': key_terms,
            'urgency': urgency,
            'original': job_text
        }
    
    def _calculate_enhanced_persona_match(self, section: Dict) -> float:
        """Enhanced persona matching with role-specific scoring."""
        score = 0.0
        content = f"{section['section_title']} {section['content']}".lower()
        
        # Role-specific scoring with weights
        if self.role in self.role_weights:
            role_terms = self.role_weights[self.role]
            for term, weight in role_terms.items():
                if term in content:
                    frequency = content.count(term)
                    score += min(weight * frequency, weight * 3)  # Cap frequency bonus
        
        # General role matching
        role_bonus = self._get_role_specific_bonus(content)
        score += role_bonus
        
        # Expertise area matching with partial credit
        for expertise_area in self.expertise:
            if expertise_area in content:
                score += 4.0
            else:
                # Partial matching for compound expertise
                expertise_words = expertise_area.split()
                if len(expertise_words) > 1:
                    matches = sum(1 for word in expertise_words if word in content)
                    partial_score = (matches / len(expertise_words)) * 2.0
                    score += partial_score
        
        return min(score, 25.0)
    
    def _get_role_specific_bonus(self, content: str) -> float:
        """Get role-specific bonus points."""
        bonus = 0.0
        
        if 'researcher' in self.role:
            research_indicators = [
                'methodology', 'experiment', 'hypothesis', 'literature review',
                'empirical', 'theoretical', 'framework', 'survey', 'investigation'
            ]
            bonus += sum(2.0 for term in research_indicators if term in content)
            
        elif 'student' in self.role:
            learning_indicators = [
                'concept', 'definition', 'example', 'tutorial', 'guide',
                'basics', 'fundamental', 'introduction', 'explanation', 'principle'
            ]
            bonus += sum(2.0 for term in learning_indicators if term in content)
            
        elif 'analyst' in self.role:
            analysis_indicators = [
                'trend', 'pattern', 'correlation', 'statistics', 'benchmark',
                'metric', 'kpi', 'performance', 'evaluation', 'assessment'
            ]
            bonus += sum(2.0 for term in analysis_indicators if term in content)
            
        elif 'developer' in self.role:
            development_indicators = [
                'implementation', 'code', 'programming', 'algorithm', 'system',
                'architecture', 'design', 'technical', 'solution', 'framework'
            ]
            bonus += sum(2.0 for term in development_indicators if term in content)
            
        elif 'manager' in self.role:
            management_indicators = [
                'strategy', 'planning', 'decision', 'leadership', 'coordination',
                'objective', 'goal', 'vision', 'policy', 'governance'
            ]
            bonus += sum(2.0 for term in management_indicators if term in content)
        
        return min(bonus, 15.0)
    
    def _calculate_enhanced_job_match(self, section: Dict, job_context: Dict) -> float:
        """Enhanced job matching using extracted context."""
        score = 0.0
        content = f"{section['section_title']} {section['content']}".lower()
        
        # Key terms matching with frequency weighting
        for term in job_context['key_terms']:
            if term in content:
                frequency = content.count(term)
                term_weight = len(term.split()) * 1.5  # Longer terms get more weight
                score += min(term_weight * frequency, term_weight * 3)
        
        # Job type specific scoring
        job_type = job_context['type']
        type_bonus = self._get_job_type_bonus(content, job_type)
        score += type_bonus
        
        # Urgency-based adjustments
        if job_context['urgency'] == 'high':
            # Prioritize summary and conclusion sections
            if any(term in section['section_title'].lower() 
                  for term in ['summary', 'conclusion', 'key', 'important']):
                score += 3.0
        elif job_context['urgency'] == 'detailed':
            # Prioritize methodology and detailed sections
            if any(term in section['section_title'].lower() 
                  for term in ['method', 'detail', 'procedure', 'process']):
                score += 3.0
        
        return min(score, 25.0)
    
    def _get_job_type_bonus(self, content: str, job_type: str) -> float:
        """Get bonus points based on job type."""
        bonus = 0.0
        
        type_indicators = {
            'research': ['methodology', 'findings', 'results', 'study', 'investigation'],
            'learning': ['concept', 'theory', 'principle', 'example', 'explanation'],
            'analysis': ['data', 'trend', 'pattern', 'evaluation', 'comparison'],
            'development': ['implementation', 'design', 'system', 'solution', 'technical'],
            'management': ['strategy', 'planning', 'objective', 'decision', 'coordination']
        }
        
        if job_type in type_indicators:
            indicators = type_indicators[job_type]
            bonus += sum(2.5 for term in indicators if term in content)
        
        return min(bonus, 12.0)
    
    def _calculate_expertise_match(self, section: Dict) -> float:
        """Calculate how well section matches stated expertise."""
        if not self.expertise:
            return 0.0
        
        score = 0.0
        content = f"{section['section_title']} {section['content']}".lower()
        
        for expertise in self.expertise:
            # Direct match
            if expertise in content:
                score += 5.0
            
            # Related terms match
            related_terms = self._get_related_terms(expertise)
            for term in related_terms:
                if term in content:
                    score += 1.0
        
        return min(score, 15.0)
    
    def _calculate_experience_level_match(self, section: Dict) -> float:
        """Adjust scoring based on experience level."""
        content = f"{section['section_title']} {section['content']}".lower()
        
        if self.experience_level == 'beginner':
            # Prefer introductory and basic content
            beginner_terms = ['introduction', 'basic', 'fundamental', 'overview', 'getting started']
            return sum(1.0 for term in beginner_terms if term in content)
            
        elif self.experience_level == 'advanced' or self.experience_level == 'senior':
            # Prefer advanced and detailed content
            advanced_terms = ['advanced', 'complex', 'detailed', 'in-depth', 'sophisticated']
            return sum(1.0 for term in advanced_terms if term in content)
        
        # Intermediate level - no specific preference
        return 0.0
    
    def _get_related_terms(self, expertise: str) -> List[str]:
        """Get related terms for an expertise area."""
        related_terms_map = {
            'machine learning': ['ml', 'neural', 'algorithm', 'model', 'training'],
            'data science': ['analytics', 'statistics', 'visualization', 'mining'],
            'software engineering': ['programming', 'development', 'coding', 'architecture'],
            'artificial intelligence': ['ai', 'intelligent', 'automation', 'cognitive'],
            'business analysis': ['requirements', 'process', 'stakeholder', 'workflow'],
            'project management': ['planning', 'scheduling', 'coordination', 'delivery']
        }
        
        return related_terms_map.get(expertise, [])
    
    def _extract_meaningful_terms(self, text: str) -> List[str]:
        """Extract meaningful terms from job description."""
        # Remove common stop words
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 
            'of', 'with', 'by', 'from', 'up', 'about', 'into', 'through', 'during',
            'before', 'after', 'above', 'below', 'between', 'among', 'this', 'that',
            'these', 'those', 'i', 'me', 'my', 'myself', 'we', 'our', 'ours', 'ourselves'
        }
        
        # Extract words and filter
        words = re.findall(r'\b[a-zA-Z]{3,}\b', text)
        meaningful_terms = []
        
        for word in words:
            word_lower = word.lower()
            if (word_lower not in stop_words and 
                len(word_lower) > 2 and 
                not word_lower.isdigit()):
                meaningful_terms.append(word_lower)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_terms = []
        for term in meaningful_terms:
            if term not in seen:
                seen.add(term)
                unique_terms.append(term)
        
        return unique_terms[:20]  # Top 20 terms
    
    def _calculate_weighted_importance(self, relevance: float, persona: float, 
                                     job: float, quality: float, domain: float,
                                     expertise: float, experience: float) -> float:
        """Calculate weighted importance score."""
        # Dynamic weights based on persona and job context
        weights = {
            'relevance': 0.25,
            'persona': 0.20,
            'job': 0.25,
            'quality': 0.10,
            'domain': 0.10,
            'expertise': 0.07,
            'experience': 0.03
        }
        
        # Adjust weights based on role
        if 'researcher' in self.role:
            weights['relevance'] = 0.30
            weights['quality'] = 0.15
        elif 'student' in self.role:
            weights['persona'] = 0.25
            weights['experience'] = 0.05
        
        total_score = (
            relevance * weights['relevance'] +
            persona * weights['persona'] +
            job * weights['job'] +
            quality * weights['quality'] +
            domain * weights['domain'] +
            expertise * weights['expertise'] +
            experience * weights['experience']
        )
        
        return round(total_score, 2)
