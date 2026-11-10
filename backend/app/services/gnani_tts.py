"""
Gnani Timbre v2.5 Text-to-Speech Integration

Provides regional-language voice feedback confirmations:
- "Rendu chairs remove panna poren."
- "Sofa and TV same place-la irukkum."
- "Layout neat-a arrange panniten."
"""
import os
import hashlib
from pathlib import Path
import requests
from typing import Dict, Any

from app.core.config import GNANI_API_KEY, GNANI_TTS_URL, RESULTS_DIR

class GnaniTTS:
    def __init__(self):
        self.api_key = GNANI_API_KEY or os.getenv("GNANI_API_KEY", "")
        self.api_url = GNANI_TTS_URL or os.getenv("GNANI_TTS_URL", "https://api.vachana.ai/api/v1/tts/inference")

    def generate_speech(self, text: str, language: str = "ta-IN") -> Dict[str, Any]:
        """
        Generate spoken audio for an arrangement confirmation message using Gnani Timbre.
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
                "X-API-Key-ID": self.api_key,
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "text": text,
                "language": language,
                "voice": "Nalini",
                "model": "timbre-v2.5",
                "speed": 1.0
            }
            resp = requests.post(self.api_url, json=payload, headers=headers, timeout=12)
            if resp.ok:
                content_type = resp.headers.get("Content-Type", "")
                if "audio" in content_type or len(resp.content) > 1000:
                    # Raw audio bytes returned from Vachana TTS inference
                    audio_hash = hashlib.md5(f"{text}_{language}".encode()).hexdigest()[:12]
                    audio_file = RESULTS_DIR / f"tts_{audio_hash}.wav"
                    with open(audio_file, "wb") as f:
                        f.write(resp.content)
                    return {
                        "text": text,
                        "audio_url": f"/storage/results/tts_{audio_hash}.wav",
                        "source": "gnani_timbre"
                    }
                else:
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
