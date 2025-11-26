import json
from typing import Dict, Any, List
from app.Config import ENV_SETTINGS
from app.core.common.llm_service import LLMService

class LLMQueryProcessor:
    def __init__(self):
        self.llm_service = LLMService()
        self.company_name = ENV_SETTINGS.COMPANY_NAME

    async def extract_search_intent(self, query: str) -> Dict[str, Any]:
        system_prompt = f"""You are an expert search query optimizer for a sales and finance AI agent representing {self.company_name}.

# Your responsibilities are:
- Analyze the user's natural language query.
- Convert it into an optimized search query for the Exa search engine.
- Focus on finding authoritative sources for finance, rates, and sales data.
- Prioritize finding current trending news related to the user's query.
- Ensure the search results will yield the latest and most appealing news stories.

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
            result = await self.llm_service.get_completion_async(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": query}
                ],
                response_format={"type": "json_object"}
            )
            return result
        except Exception as e:
            print(f"Error in LLM query processing: {e}")
            return {
                "original_query": query,
                "intent": "general",
                "cleaned_query": query,
                "search_keywords": query.split()
            }
