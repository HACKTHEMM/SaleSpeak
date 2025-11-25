import json
from typing import Dict, Any, List
from groq import Groq
from app.Config import ENV_SETTINGS

class LLMQueryProcessor:
    def __init__(self):
        self.client = Groq(api_key=ENV_SETTINGS.GROQ_API_KEY)
        self.model = ENV_SETTINGS.MODEL_ID
        self.company_name = ENV_SETTINGS.COMPANY_NAME

    def extract_search_intent(self, query: str) -> Dict[str, Any]:
        system_prompt = f"""You are an expert search query optimizer for a sales and finance AI agent representing {self.company_name}.

# Your responsibilities are:
- Analyze the user's natural language query.
- Convert it into an optimized search query for the Exa search engine.
- Focus on finding authoritative sources for finance, rates, and sales data.

# CRITICAL INSTRUCTIONS FOR QUERY GENERATION:
- If the query is about {self.company_name}, ensure the company name is prominent.
- 'cleaned_query' should be a natural language string but optimized for semantic search.
- Output MUST be valid JSON.

# Output JSON format:
{{
    "original_query": "string",
    "intent": "informational" | "commercial" | "navigational",
    "cleaned_query": "string (optimized for search engine)",
    "search_keywords": ["list", "of", "keywords"],
    "date_range": "string (optional, e.g., '2024-01-01' if relevant)"
}}
"""

        try:
            completion = self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": query}
                ],
                model=self.model,
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(completion.choices[0].message.content)
            return result
        except Exception as e:
            print(f"Error in LLM query processing: {e}")
            return {
                "original_query": query,
                "intent": "general",
                "cleaned_query": query,
                "search_keywords": query.split()
            }
