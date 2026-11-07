"""
Gnani Timbre v2.5 Text-to-Speech Integration

Provides regional-language voice feedback confirmations:
- "Rendu chairs remove panna poren."
- "Sofa and TV same place-la irukkum."
- "Layout neat-a arrange panniten."
"""
import os
import requests
from typing import Dict, Any

GNANI_API_KEY = os.getenv("GNANI_API_KEY", "")
GNANI_TTS_URL = os.getenv("GNANI_TTS_URL", "https://tts.gnani.ai/api/v1/tts")

class GnaniTTS:
    def __init__(self):
        self.api_key = GNANI_API_KEY
        self.api_url = GNANI_TTS_URL

    def generate_speech(self, text: str, language: str = "ta-IN") -> Dict[str, Any]:
        """
        Generate spoken audio for an arrangement confirmation message.
        """
        if not self.api_key:
            return {
                "text": text,
                "audio_url": None,
                "source": "none",
                "message": "TTS requires GNANI_API_KEY"
            }

        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "text": text,
                "language": language,
                "voice": "female_1",
                "speed": 1.0
            }
            resp = requests.post(self.api_url, json=payload, headers=headers, timeout=10)
            if resp.ok:
                data = resp.json()
                return {
                    "text": text,
                    "audio_url": data.get("audio_url"),
                    "source": "gnani_timbre"
                }
        except Exception as e:
            print(f"[GnaniTTS] error: {e}")

        return {
            "text": text,
            "audio_url": None,
            "source": "none"
        }
