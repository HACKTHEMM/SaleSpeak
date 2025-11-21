import re
from typing import Dict, Any, List
from app.Config import ENV_SETTINGS

class BasicQueryProcessor:
    def __init__(self):
        self.company_name = ENV_SETTINGS.COMPANY_NAME
    
    def extract_search_intent(self, query: str) -> Dict[str, Any]:
        query_lower = query.lower()
        
        intent = "general"
        if any(word in query_lower for word in ["what", "who", "when", "where", "why", "how"]):
            intent = "informational"
        elif any(word in query_lower for word in ["buy", "price", "cost", "cheap", "rate", "interest"]):
            intent = "commercial"
        
        enhanced_query = self._enhance_query(query)
        
        return {
            "original_query": query,
            "intent": intent,
            "cleaned_query": self._clean_query(enhanced_query)
        }
    
    def _enhance_query(self, query: str) -> str:
        query_lower = query.lower()
        company_lower = self.company_name.lower()
        
        if company_lower not in query_lower:
            keywords = [
                "interest rate", "rate", "loan", "lending", "borrow", 
                "invest", "return", "features", "benefits", "terms",
                "charges", "fees", "eligibility", "process"
            ]
            if any(keyword in query_lower for keyword in keywords):
                return f"{self.company_name} {query}"
        
        return query
    
    def _clean_query(self, query: str) -> str:
        cleaned = re.sub(r'[^\w\s\?\.\-]', '', query)
        return cleaned.strip()
    
    def generate_search_queries(self, query: str) -> List[str]:
        cleaned = self._clean_query(query)
        return [cleaned]
