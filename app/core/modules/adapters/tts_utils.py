import re

LANGUAGE_DICT = {
    "English": {
        "Neerja": "en-IN-NeerjaNeural",
        "Prabhat": "en-IN-PrabhatNeural",
        "Jenny": "en-US-JennyNeural",
    },
    "Hindi": {
        "Madhur": "hi-IN-MadhurNeural",
        "Swara": "hi-IN-SwaraNeural",
    },
}

DEFAULT_SPEAKERS = {
    "English": "Neerja",
    "Hindi": "Swara"
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

