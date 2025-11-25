import os
import requests
from typing import List, Dict, Any, Optional
from app.Config import ENV_SETTINGS
from .config import DEFAULT_NUM_RESULTS

class ExaSearcher:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or ENV_SETTINGS.EXA_API_KEY or os.getenv("EXA_API_KEY")
        self.base_url = "https://api.exa.ai/search"

    def search(self, query: str, num_results: int = DEFAULT_NUM_RESULTS, use_autoprompt: bool = True) -> Dict[str, Any]:
        if not query:
            return {"error": "Empty query"}
            
        if not self.api_key:
            return {"error": "Missing EXA API Key"}
            
        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json"
        }
        
        payload = {
            "query": query,
            "numResults": num_results,
            "useAutoprompt": use_autoprompt,
            "contents": {
                "text": True,
                "highlights": True
            }
        }
        
        try:
            response = requests.post(self.base_url, json=payload, headers=headers)
            response.raise_for_status()
            results = response.json()
            
            return self._process_results(results, query)
            
        except Exception as e:
            print(f"Exa Search error: {e}")
            return {"error": str(e)}
    
    def _process_results(self, results: Dict[str, Any], query: str) -> Dict[str, Any]:
        processed = {
            "query": query,
            "results": [],
            "autoprompt_string": results.get("autopromptString")
        }
        
        if "results" in results:
            for item in results["results"]:
                processed["results"].append({
                    "title": item.get("title"),
                    "url": item.get("url"),
                    "id": item.get("id"),
                    "score": item.get("score"),
                    "published_date": item.get("publishedDate"),
                    "author": item.get("author"),
                    "text": item.get("text"),
                    "highlights": item.get("highlights")
                })
                
        return processed
