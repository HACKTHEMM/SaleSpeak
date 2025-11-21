def detect_input_language(text: str) -> str:
    hindi_chars = sum(1 for char in text if '\u0900' <= char <= '\u097F')
    english_chars = sum(1 for char in text if char.isalpha() and not ('\u0900' <= char <= '\u097F'))
    total_alpha_chars = hindi_chars + english_chars
    
    if total_alpha_chars == 0:
        return "english"
    
    hindi_ratio = hindi_chars / total_alpha_chars
    english_ratio = english_chars / total_alpha_chars
    
    if hindi_ratio > 0.1 and english_ratio > 0.1:
        return "hinglish"
    elif hindi_ratio > 0.3:
        return "hindi"
    else:
        return "english"

def contains_hindi(text: str) -> bool:
    hindi_chars = sum(1 for char in text if '\u0900' <= char <= '\u097F')
    return hindi_chars > 0

def is_hinglish_response(text: str) -> bool:
    hindi_chars = sum(1 for char in text if '\u0900' <= char <= '\u097F')
    english_chars = sum(1 for char in text if char.isalpha() and not ('\u0900' <= char <= '\u097F'))
    
    return hindi_chars > 0 and english_chars > 0
