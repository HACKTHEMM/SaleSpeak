from typing import Dict, Any, Optional
from .searcher import ExaSearcher
from .query_processor import LLMQueryProcessor

def get_web_data_for_llm(query: str, exa_api_key: Optional[str] = None) -> Dict[str, Any]:
    processor = LLMQueryProcessor()
    searcher = ExaSearcher(exa_api_key)

    intent_data = processor.extract_search_intent(query)
    
    search_query = intent_data.get("cleaned_query", query)
    
    results = searcher.search(search_query)

    return _format_for_llm(results, intent_data)

def _format_for_llm(results: Dict[str, Any], intent_data: Dict[str, Any]) -> Dict[str, Any]:
    formatted = {
        "query_analysis": intent_data,
        "search_results": [],
        "summary_points": []
    }
    
    if "error" in results:
        formatted["error"] = results["error"]
        return formatted
        
    if results.get("autoprompt_string"):
        formatted["query_analysis"]["exa_autoprompt"] = results["autoprompt_string"]

    for item in results.get("results", []):
        entry = {
            "title": item.get("title"),
            "url": item.get("url"),
            "published": item.get("published_date"),
            "highlights": item.get("highlights"),
            "text_snippet": item.get("text")[:500] if item.get("text") else None 
        }
        formatted["search_results"].append(entry)
        
        if item.get("highlights"):
            formatted["summary_points"].append(f"From {item.get('title')}: {item.get('highlights')}")
        elif item.get("text"):
             formatted["summary_points"].append(f"From {item.get('title')}: {item.get('text')[:200]}...")
            
    return formatted

def get_web_search_results(query: str, num_results: int = 5) -> Dict[str, Any]:
    searcher = ExaSearcher()
    return searcher.search(query, num_results)
