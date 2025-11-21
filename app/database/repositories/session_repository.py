import os
import time
from typing import Dict, Optional, Any


class SessionRepository:
    
    def __init__(self):
        self.session_responses: Dict[str, Dict[str, Any]] = {}
    
    def store_session_response(self, session_id: str, text: str, audio_file_path: str) -> None:
        self.session_responses[session_id] = {
            "text": text,
            "audio_file": audio_file_path,
            "audio_filename": os.path.basename(audio_file_path) if audio_file_path else "",
            "timestamp": time.time()
        }
    
    def get_session_response(self, session_id: str) -> Optional[Dict[str, Any]]:
        return self.session_responses.get(session_id)
    
    def session_exists(self, session_id: str) -> bool:
        return session_id in self.session_responses
    
    def get_all_session_ids(self) -> list:
        return list(self.session_responses.keys())
    
    def get_audio_file_path(self, session_id: str) -> str:
        session_data = self.session_responses.get(session_id)
        return session_data.get("audio_file", "") if session_data else ""
    
    @staticmethod
    def normalize_audio_path(audio_path: str) -> str:
        if not audio_path:
            return ""

        if not os.path.isabs(audio_path):
            audio_path = os.path.abspath(audio_path)

        audio_path = os.path.normpath(audio_path)

        return audio_path
    
    @staticmethod
    def find_audio_file(audio_file_path: str) -> str:
        if not audio_file_path:
            return ""

        possible_paths = []

        possible_paths.append(audio_file_path)

        if not os.path.isabs(audio_file_path):
            possible_paths.append(os.path.abspath(audio_file_path))

        filename = os.path.basename(audio_file_path)
        static_audio_dir = os.path.join("static", "audio")
        possible_paths.append(os.path.join(static_audio_dir, filename))
        possible_paths.append(os.path.abspath(
            os.path.join(static_audio_dir, filename)))
        script_dir = os.path.dirname(os.path.abspath(__file__))
        possible_paths.append(os.path.join(
            script_dir, "..", "..", "..", static_audio_dir, filename))
        possible_paths.append(os.path.join(
            script_dir, "..", "..", static_audio_dir, filename))

        for path in possible_paths:
            normalized_path = os.path.normpath(path)
            if os.path.exists(normalized_path):
                return normalized_path

        return ""
    
    @staticmethod
    def get_audio_urls(session_id: str, audio_file_path: str) -> Dict[str, str]:
        audio_url = ""
        static_audio_url = ""
        direct_audio_endpoint = ""

        if audio_file_path:
            direct_audio_endpoint = f"/get-audio/{session_id}"
            audio_url = direct_audio_endpoint

            audio_filename = os.path.basename(audio_file_path)
            static_audio_url = f"/static/audio/{audio_filename}"

        return {
            "audio_url": audio_url,
            "static_audio_url": static_audio_url,
            "direct_audio_endpoint": direct_audio_endpoint
        }
    
    def get_debug_info(self, session_id: str) -> Dict[str, Any]:
        debug_info = {
            "session_id": session_id,
            "session_exists": session_id in self.session_responses,
            "all_sessions": list(self.session_responses.keys()),
            "session_data": None,
            "file_checks": {},
            "static_directory": {},
            "working_directory": os.getcwd()
        }

        if session_id in self.session_responses:
            session_data = self.session_responses[session_id]
            debug_info["session_data"] = {
                "text_length": len(session_data.get("text", "")),
                "audio_file": session_data.get("audio_file", ""),
                "audio_filename": session_data.get("audio_filename", ""),
                "timestamp": session_data.get("timestamp", 0)
            }

            audio_file_path = session_data.get("audio_file", "")
            if audio_file_path:
                debug_info["file_checks"]["original_path"] = {
                    "path": audio_file_path,
                    "exists": os.path.exists(audio_file_path),
                    "is_absolute": os.path.isabs(audio_file_path)
                }

                if os.path.exists(audio_file_path):
                    debug_info["file_checks"]["original_path"]["size"] = os.path.getsize(
                        audio_file_path)
                    debug_info["file_checks"]["original_path"]["modified"] = time.ctime(
                        os.path.getmtime(audio_file_path))

                abs_path = os.path.abspath(audio_file_path)
                debug_info["file_checks"]["absolute_path"] = {
                    "path": abs_path,
                    "exists": os.path.exists(abs_path)
                }

                filename = os.path.basename(audio_file_path)
                static_path = os.path.join("static", "audio", filename)
                debug_info["file_checks"]["static_path"] = {
                    "path": static_path,
                    "exists": os.path.exists(static_path)
                }

        static_audio_dir = os.path.join("static", "audio")
        if os.path.exists(static_audio_dir):
            try:
                files = os.listdir(static_audio_dir)
                debug_info["static_directory"] = {
                    "path": static_audio_dir,
                    "exists": True,
                    "file_count": len(files),
                    "recent_files": sorted(
                        files, 
                        key=lambda x: os.path.getmtime(os.path.join(static_audio_dir, x)), 
                        reverse=True
                    )[:5]
                }
            except Exception as e:
                debug_info["static_directory"] = {
                    "path": static_audio_dir,
                    "exists": True,
                    "error": str(e)
                }
        else:
            debug_info["static_directory"] = {
                "path": static_audio_dir,
                "exists": False
            }

        return debug_info


# Create singleton instance
session_repo = SessionRepository()
