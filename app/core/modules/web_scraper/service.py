from typing import Dict, Any, Optional, List
from .searcher import WebSearcher
from .query_processor import BasicQueryProcessor

def get_web_data_for_llm(query: str, serpapi_key: Optional[str] = None) -> Dict[str, Any]:
    processor = BasicQueryProcessor()
    searcher = WebSearcher(serpapi_key)

    intent_data = processor.extract_search_intent(query)
    cleaned_query = intent_data.get("cleaned_query", query)

    results = searcher.search(cleaned_query)

    return _format_for_llm(results, intent_data)

def _format_for_llm(results: Dict[str, Any], intent_data: Dict[str, Any]) -> Dict[str, Any]:
    formatted = {
        "query_info": intent_data,
        "summary": [],
        "detailed_results": [],
        "quick_facts": []
    }
    
    if "error" in results:
        formatted["error"] = results["error"]
        return formatted
        
    if results.get("answer_box"):
        answer_box = results["answer_box"]
        formatted["quick_facts"].append(answer_box)
        if isinstance(answer_box, dict):
            if answer_box.get("answer"):
                formatted["summary"].append(f"Direct Answer: {answer_box['answer']}")
            if answer_box.get("snippet"):
                formatted["summary"].append(f"Key Info: {answer_box['snippet']}")
        
    if results.get("knowledge_graph"):
        kg = results["knowledge_graph"]
        formatted["quick_facts"].append(kg)
        if isinstance(kg, dict):
            if kg.get("description"):
                formatted["summary"].append(f"About: {kg['description']}")
        
    if results.get("related_questions"):
        for qa in results["related_questions"][:3]:
            if qa.get("question") and qa.get("snippet"):
                formatted["summary"].append(f"Q: {qa['question']} - A: {qa['snippet']}")
        
    for item in results.get("organic_results", []):
        formatted["detailed_results"].append({
            "title": item.get("title"),
            "link": item.get("link"),
            "content": item.get("snippet")
        })
        if item.get("snippet"):
            formatted["summary"].append(f"{item.get('title')}: {item.get('snippet')}")
            
    return formatted

def get_web_search_results(query: str, num_results: int = 5) -> Dict[str, Any]:
    searcher = WebSearcher()
    return searcher.search(query, num_results)
