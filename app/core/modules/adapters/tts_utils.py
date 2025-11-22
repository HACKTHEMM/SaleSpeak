import re

LANGUAGE_DICT = {
    "English": {
        "Rachel": "21m00Tcm4TlvDq8ikWAM", 
        "Adam": "pNInz6obpgDQGcFmaJgB", 
        "Nicole": "piTKgcLEGmPE4e6mEKli",   
    },
    "Hindi": {
        "Monika": "1qEiC6qsybMkmnNdVMbK",
        "Monika2": "kvQSb3naDTi3sgHwwBC1"
    },
}

DEFAULT_SPEAKERS = {
    "English": "Rachel",
    "Hindi": "Monika2"
}

HINDI_DETECTION_THRESHOLD = 0.25

def detect_language(text: str) -> str:
    hindi_pattern = r'[\u0900-\u097F]'
    
    text_cleaned = re.sub(r'[^\w\s]', '', text.strip())
    
    hindi_chars = len(re.findall(hindi_pattern, text_cleaned))
    total_chars = len(text_cleaned.replace(' ', ''))
    
    if total_chars > 0 and (hindi_chars / total_chars) > HINDI_DETECTION_THRESHOLD:
        return "Hindi"
    else:
        return "English"

