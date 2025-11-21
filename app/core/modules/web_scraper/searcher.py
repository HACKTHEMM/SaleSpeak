import os
import time
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from serpapi import GoogleSearch
from dotenv import load_dotenv
from app.Config import ENV_SETTINGS
from .config import DEFAULT_NUM_RESULTS, DEFAULT_LOCATION

load_dotenv()

class WebSearcher:

    def __init__(self, serpapi_key: Optional[str] = None, max_workers: int = 5):
        self.api_key = serpapi_key or ENV_SETTINGS.SERP_API_KEY or os.getenv("SERP_API_KEY")
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        
    def search(self, query: str, num_results: int = DEFAULT_NUM_RESULTS, location: str = DEFAULT_LOCATION) -> Dict[str, Any]:
        if not query:
            return {"error": "Empty query"}
            
        if not self.api_key:
            return {"error": "Missing SERP API Key"}
            
        try:
            params = {
                "q": query,
                "location": location,
                "hl": "en",
                "gl": "in" if location == "India" else "us",
                "google_domain": "google.co.in" if location == "India" else "google.com",
                "num": num_results,
                "api_key": self.api_key
            }
            
            search = GoogleSearch(params)
            results = search.get_dict()
            
            return self._process_results(results, query)
            
        except Exception as e:
            print(f"Search error: {e}")
            return {"error": str(e)}
    
    def _process_results(self, results: Dict[str, Any], query: str) -> Dict[str, Any]:
        processed = {
            "query": query,
            "organic_results": [],
            "answer_box": None,
            "knowledge_graph": None,
            "related_questions": []
        }
        
        if "organic_results" in results:
            for item in results["organic_results"]:
                processed["organic_results"].append({
                    "title": item.get("title"),
                    "link": item.get("link"),
                    "snippet": item.get("snippet"),
                    "position": item.get("position")
                })
                
        if "answer_box" in results:
            processed["answer_box"] = results["answer_box"]
            
        if "knowledge_graph" in results:
            processed["knowledge_graph"] = results["knowledge_graph"]
            
        if "related_questions" in results:
            for item in results["related_questions"]:
                processed["related_questions"].append({
                    "question": item.get("question"),
                    "snippet": item.get("snippet"),
                    "link": item.get("link")
                })
                
        return processed
        
    def multi_search(self, queries: List[str], num_results: int = DEFAULT_NUM_RESULTS) -> Dict[str, Any]:
        results = {}
        futures = {}
        
        for query in queries:
            future = self.executor.submit(self.search, query, num_results)
            futures[future] = query
            
        for future in as_completed(futures):
            query = futures[future]
            try:
                results[query] = future.result()
            except Exception as e:
                results[query] = {"error": str(e)}
                
        return results
