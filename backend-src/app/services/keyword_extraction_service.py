from typing import List, Dict, Any, Optional
import logging
import re
from .nlp_service import NLPService

logger = logging.getLogger(__name__)


class KeywordExtractionService:
    """Service for extracting structured keywords from user search queries"""
    
    def __init__(self):
        self.nlp_service = NLPService()
        
        # Common job title patterns
        self.job_title_patterns = [
            r'\b(?:software|backend|frontend|full.?stack|fullstack|devops|data|machine.?learning|ml|ai)\s+(?:engineer|developer|architect|scientist|analyst|specialist)\b',
            r'\b(?:product|project|program|engineering|technical)\s+(?:manager|lead|director)\b',
            r'\b(?:senior|junior|entry.?level|mid.?level|lead|principal|staff)\s+(?:engineer|developer|architect|scientist|analyst)\b',
            r'\b(?:senior|junior|entry.?level|mid.?level|lead|principal|staff)\s+(?:software|backend|frontend|full.?stack|fullstack|devops|data|machine.?learning|ml|ai)\s+(?:engineer|developer|architect|scientist|analyst)\b',
        ]
        
        # Common job title keywords
        self.job_title_keywords = [
            'engineer', 'developer', 'programmer', 'architect', 'scientist',
            'analyst', 'manager', 'director', 'lead', 'specialist', 'consultant',
            'designer', 'administrator', 'coordinator', 'assistant'
        ]
    
    def extract_keywords(self, query: str) -> Dict[str, Any]:
        """
        Extract structured keywords from user query
        
        Args:
            query: User search query text
            
        Returns:
            Dictionary with extracted keywords:
            {
                "job_titles": List[str],
                "skills": List[str],
                "salary": {"min": int, "max": int} or None,
                "locations": List[str]
            }
        """
        if not query or not query.strip():
            return {
                "job_titles": [],
                "skills": [],
                "salary": None,
                "locations": []
            }
        
        try:
            # Extract job titles
            job_titles = self._extract_job_titles(query)
            
            # Extract skills
            skills = self._extract_skills(query)
            
            # Extract salary
            salary = self._extract_salary(query)
            
            # Extract locations
            locations = self._extract_locations(query)
            
            return {
                "job_titles": job_titles,
                "skills": skills,
                "salary": salary,
                "locations": locations
            }
            
        except Exception as e:
            logger.error(f"Error extracting keywords from query: {e}")
            return {
                "job_titles": [],
                "skills": [],
                "salary": None,
                "locations": []
            }
    
    def _extract_job_titles(self, query: str) -> List[str]:
        """Extract job titles from query"""
        job_titles = set()
        
        # Use pattern matching
        for pattern in self.job_title_patterns:
            matches = re.findall(pattern, query, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    # Join tuple matches
                    title = ' '.join(m for m in match if m).strip()
                else:
                    title = match.strip()
                if title:
                    job_titles.add(title)
        
        # Use spaCy NER for capitalized phrases that might be job titles
        if self.nlp_service.nlp:
            try:
                doc = self.nlp_service.nlp(query)
                # Look for noun phrases that contain job title keywords
                for chunk in doc.noun_chunks:
                    chunk_text = chunk.text.lower()
                    if any(keyword in chunk_text for keyword in self.job_title_keywords):
                        # Check if it's a proper job title pattern
                        if len(chunk.text.split()) <= 4:  # Reasonable job title length
                            job_titles.add(chunk.text.strip())
            except Exception as e:
                logger.warning(f"Error extracting job titles with spaCy: {e}")
        
        # Extract common job title phrases manually
        # Look for patterns like "Software Engineer", "Data Scientist", etc.
        title_phrases = re.findall(
            r'\b(?:software|backend|frontend|full.?stack|fullstack|devops|data|machine.?learning|ml|ai|product|project|engineering|technical)\s+(?:engineer|developer|architect|scientist|analyst|specialist|manager|lead|director)\b',
            query,
            re.IGNORECASE
        )
        for phrase in title_phrases:
            job_titles.add(phrase.strip())
        
        # Also look for experience level + job title combinations
        experience_levels = ['senior', 'junior', 'entry level', 'mid level', 'lead', 'principal', 'staff']
        for level in experience_levels:
            pattern = rf'\b{level}\s+(?:software|backend|frontend|full.?stack|fullstack|devops|data|machine.?learning|ml|ai)?\s*(?:engineer|developer|architect|scientist|analyst|specialist)\b'
            matches = re.findall(pattern, query, re.IGNORECASE)
            for match in matches:
                job_titles.add(match.strip())
        
        return list(job_titles)
    
    def _extract_skills(self, query: str) -> List[str]:
        """Extract skills from query using existing NLP service and semantic matching"""
        skills = set()
        
        # Use existing skill extraction
        extracted_skills = self.nlp_service.extract_skills_from_text(query)
        skills.update(extracted_skills)
        
        # Use sentence transformer for semantic skill matching
        # Find skills that are semantically similar to common tech skills
        if self.nlp_service.sentence_transformer:
            try:
                # Common tech skills to match against
                common_skills = [
                    'Python', 'Java', 'JavaScript', 'React', 'Node.js', 'Django', 'Flask',
                    'AWS', 'Docker', 'Kubernetes', 'SQL', 'PostgreSQL', 'MongoDB',
                    'Machine Learning', 'TensorFlow', 'PyTorch', 'Data Science',
                    'DevOps', 'CI/CD', 'Microservices', 'REST API', 'GraphQL'
                ]
                
                # Get embeddings for query and common skills
                query_embedding = self.nlp_service.sentence_transformer.encode([query])[0]
                skill_embeddings = self.nlp_service.sentence_transformer.encode(common_skills)
                
                # Calculate similarity
                import numpy as np
                similarities = np.dot(skill_embeddings, query_embedding) / (
                    np.linalg.norm(skill_embeddings, axis=1) * np.linalg.norm(query_embedding)
                )
                
                # Add skills with high similarity (>0.5)
                for i, similarity in enumerate(similarities):
                    if similarity > 0.5:
                        skills.add(common_skills[i])
            except Exception as e:
                logger.warning(f"Error in semantic skill matching: {e}")
        
        # Also extract skills mentioned explicitly (capitalized tech terms)
        tech_terms = re.findall(
            r'\b(?:[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b',
            query
        )
        # Filter out common non-tech words
        non_tech_words = {'Software', 'Engineer', 'Developer', 'California', 'California', 'United', 'States'}
        for term in tech_terms:
            if term not in non_tech_words and len(term) > 2:
                # Check if it looks like a tech skill
                if self._is_likely_tech_skill(term):
                    skills.add(term)
        
        return list(skills)
    
    def _is_likely_tech_skill(self, term: str) -> bool:
        """Check if a term is likely a tech skill"""
        tech_indicators = [
            'js', 'jsx', 'ts', 'py', 'java', 'go', 'rust', 'swift', 'kotlin',
            'api', 'sdk', 'sql', 'nosql', 'db', 'orm', 'http', 'https',
            'ui', 'ux', 'css', 'html', 'xml', 'json', 'yaml', 'toml'
        ]
        term_lower = term.lower()
        return any(indicator in term_lower for indicator in tech_indicators) or \
               term in ['React', 'Angular', 'Vue', 'Django', 'Flask', 'Express', 'Spring']
    
    def _extract_salary(self, query: str) -> Optional[Dict[str, int]]:
        """Extract salary information from query"""
        salary_patterns = [
            r'\$(\d+)[kK]',  # $80k, $100K
            r'\$(\d{1,3}(?:,\d{3})*)',  # $80,000, $100,000
            r'(\d+)[kK]\s*(?:annual|yearly|per year|salary)',  # 80k annual
            r'(\d+)\s*(?:thousand|k)\s*(?:annual|yearly|per year|salary|dollars)',  # 80 thousand annual
            r'salary\s*(?:of|is|:)?\s*\$?(\d+)[kK]?',  # salary of $80k
            r'(\d+)[kK]?\s*(?:to|-)\s*(\d+)[kK]?\s*(?:annual|yearly|per year)',  # 80k to 100k annual
        ]
        
        min_salary = None
        max_salary = None
        
        for pattern in salary_patterns:
            matches = re.finditer(pattern, query, re.IGNORECASE)
            for match in matches:
                groups = match.groups()
                if len(groups) == 1:
                    # Single salary value
                    value_str = groups[0].replace(',', '')
                    try:
                        value = int(value_str)
                        # Check if it's in thousands (k suffix or context)
                        if 'k' in match.group(0).lower() or value < 1000:
                            value = value * 1000
                        
                        if min_salary is None or value < min_salary:
                            min_salary = value
                        if max_salary is None or value > max_salary:
                            max_salary = value
                    except ValueError:
                        continue
                elif len(groups) == 2:
                    # Range
                    try:
                        val1 = int(groups[0].replace(',', ''))
                        val2 = int(groups[1].replace(',', ''))
                        
                        # Check for k suffix
                        if 'k' in match.group(0).lower():
                            val1 = val1 * 1000
                            val2 = val2 * 1000
                        
                        min_salary = min(val1, val2) if min_salary is None else min(min_salary, val1, val2)
                        max_salary = max(val1, val2) if max_salary is None else max(max_salary, val1, val2)
                    except ValueError:
                        continue
        
        # Also check MONEY entities from spaCy
        if self.nlp_service.nlp:
            try:
                entities = self.nlp_service.extract_entities_from_text(query)
                money_entities = entities.get('MONEY', [])
                for money in money_entities:
                    # Extract numeric value from money string
                    numbers = re.findall(r'\d+', money.replace(',', ''))
                    if numbers:
                        try:
                            value = int(numbers[0])
                            # Heuristic: if value < 1000, assume it's in thousands
                            if value < 1000:
                                value = value * 1000
                            
                            if min_salary is None or value < min_salary:
                                min_salary = value
                            if max_salary is None or value > max_salary:
                                max_salary = value
                        except ValueError:
                            continue
            except Exception as e:
                logger.warning(f"Error extracting salary from entities: {e}")
        
        if min_salary is None and max_salary is None:
            return None
        
        # If only one value found, use it as both min and max
        if min_salary is None:
            min_salary = max_salary
        if max_salary is None:
            max_salary = min_salary
        
        return {
            "min": min_salary,
            "max": max_salary
        }
    
    def _extract_locations(self, query: str) -> List[str]:
        """Extract location information from query"""
        locations = set()
        
        # Use spaCy GPE entities
        if self.nlp_service.nlp:
            try:
                entities = self.nlp_service.extract_entities_from_text(query)
                gpe_entities = entities.get('GPE', [])
                locations.update(gpe_entities)
                
                # Also check LOC entities
                loc_entities = entities.get('LOC', [])
                locations.update(loc_entities)
            except Exception as e:
                logger.warning(f"Error extracting locations with spaCy: {e}")
        
        # Pattern matching for common location formats
        location_patterns = [
            r'\b(?:in|at|near|from)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*),?\s*([A-Z]{2})?\b',  # "in San Francisco, CA"
            r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*),?\s*([A-Z]{2})\b',  # "San Francisco, CA"
            r'\b(?:in|at|near|from)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b',  # "in California"
        ]
        
        for pattern in location_patterns:
            matches = re.finditer(pattern, query)
            for match in matches:
                groups = match.groups()
                location_parts = [g for g in groups if g]
                if location_parts:
                    location = ', '.join(location_parts)
                    locations.add(location.strip())
        
        # Common US states and cities
        us_states = [
            'California', 'New York', 'Texas', 'Florida', 'Illinois',
            'Pennsylvania', 'Ohio', 'Georgia', 'North Carolina', 'Michigan',
            'New Jersey', 'Virginia', 'Washington', 'Arizona', 'Massachusetts',
            'Tennessee', 'Indiana', 'Missouri', 'Maryland', 'Wisconsin'
        ]
        
        us_cities = [
            'San Francisco', 'New York', 'Los Angeles', 'Chicago', 'Houston',
            'Phoenix', 'Philadelphia', 'San Antonio', 'San Diego', 'Dallas',
            'San Jose', 'Austin', 'Jacksonville', 'Fort Worth', 'Columbus',
            'Charlotte', 'Seattle', 'Denver', 'Boston', 'El Paso'
        ]
        
        query_lower = query.lower()
        for state in us_states:
            if state.lower() in query_lower:
                locations.add(state)
        
        for city in us_cities:
            if city.lower() in query_lower:
                locations.add(city)
        
        # Check for "Remote" keyword
        if re.search(r'\bremote\b', query, re.IGNORECASE):
            locations.add('Remote')
        
        return list(locations)






