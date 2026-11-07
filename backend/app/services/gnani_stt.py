"""
Gnani Prisma v2.5 Speech-to-Text Integration

Converts Tanglish / Tamil / English audio into text transcripts.
Supports both the live Gnani Prisma API and a robust local fallback
using Google's SpeechRecognition library for offline/demo scenarios.
"""
import os
import io
import json
import wave
import tempfile
import requests
from pathlib import Path
from typing import Dict, Any, Optional

# Gnani API Configuration
GNANI_API_KEY = os.getenv("GNANI_API_KEY", "")
GNANI_API_URL = os.getenv("GNANI_API_URL", "https://asr.gnani.ai/api/v1/asr")
GNANI_LANG = os.getenv("GNANI_LANG", "en-IN")  # en-IN for Tanglish/English, ta-IN for Tamil


class GnaniSTT:
    """
    Gnani Prisma v2.5 Speech-to-Text service.
    
    Priority order:
    1. Gnani Prisma cloud API (if API key is set)
    2. Google Web Speech API fallback (for demos without Gnani credentials)
    3. Manual text input passthrough (always available)
    """

    def __init__(self):
        self.api_key = GNANI_API_KEY
        self.api_url = GNANI_API_URL
        self.language = GNANI_LANG
        self._check_gnani_available()

    def _check_gnani_available(self):
        if self.api_key:
            print(f"[GnaniSTT] Prisma API key configured. Language: {self.language}")
        else:
            print("[GnaniSTT] No GNANI_API_KEY set. Will use fallback STT for demos.")

    def transcribe_audio(self, audio_path: str, language: Optional[str] = None) -> Dict[str, Any]:
        """
        Transcribe an audio file to text.
        
        Args:
            audio_path: Path to WAV/WebM/OGG audio file
            language: Override language code (e.g., 'ta-IN', 'en-IN')
            
        Returns:
            {
                "transcript": "full text transcript",
                "language": "detected or configured language",
                "confidence": 0.0-1.0,
                "words": [{"word": "sofa", "start": 0.5, "end": 0.8}],
                "source": "gnani_prisma" | "google_fallback" | "manual"
            }
        """
        lang = language or self.language

        # Try Gnani Prisma first
        if self.api_key:
            try:
                result = self._transcribe_gnani(audio_path, lang)
                if result and result.get("transcript"):
                    return result
            except Exception as e:
                print(f"[GnaniSTT] Prisma API error: {e}. Falling back.")

        # Fallback to Google SpeechRecognition
        try:
            result = self._transcribe_google_fallback(audio_path, lang)
            if result and result.get("transcript"):
                return result
        except Exception as e:
            print(f"[GnaniSTT] Google fallback error: {e}. Returning empty result.")

        return {
            "transcript": "",
            "language": lang,
            "confidence": 0.0,
            "words": [],
            "source": "none",
            "error": "Could not transcribe audio. Please type your instruction manually."
        }

    def _transcribe_gnani(self, audio_path: str, lang: str) -> Dict[str, Any]:
        """Call Gnani Prisma v2.5 hosted API."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json"
        }
        
        with open(audio_path, "rb") as f:
            files = {"file": (Path(audio_path).name, f, "audio/wav")}
            data = {
                "lang": lang,
                "punctuation": "true",
                "itn": "true",  # Inverse text normalization
            }
            
            response = requests.post(
                self.api_url,
                headers=headers,
                files=files,
                data=data,
                timeout=30
            )

        if response.status_code != 200:
            raise Exception(f"Gnani API returned {response.status_code}: {response.text[:200]}")

        result = response.json()
        
        # Extract transcript from Gnani response format
        transcript = ""
        words = []
        confidence = 0.0
        
        if "result" in result:
            transcript = result["result"].get("transcript", "")
            confidence = result["result"].get("confidence", 0.85)
            raw_words = result["result"].get("words", [])
            words = [
                {"word": w.get("word", ""), "start": w.get("start", 0), "end": w.get("end", 0)}
                for w in raw_words
            ]
        elif "transcript" in result:
            transcript = result["transcript"]
            confidence = result.get("confidence", 0.85)

        return {
            "transcript": transcript,
            "language": lang,
            "confidence": confidence,
            "words": words,
            "source": "gnani_prisma"
        }

    def _transcribe_google_fallback(self, audio_path: str, lang: str) -> Dict[str, Any]:
        """Fallback using Google Web Speech API via SpeechRecognition library."""
        try:
            import speech_recognition as sr
        except ImportError:
            raise Exception("speech_recognition not installed. Run: pip install SpeechRecognition")

        recognizer = sr.Recognizer()
        
        # Convert to WAV if needed
        wav_path = self._ensure_wav(audio_path)
        
        with sr.AudioFile(wav_path) as source:
            audio = recognizer.record(source)

        # Map language codes
        sr_lang = "en-IN"
        if "ta" in lang.lower():
            sr_lang = "ta-IN"
        elif "hi" in lang.lower():
            sr_lang = "hi-IN"

        try:
            transcript = recognizer.recognize_google(audio, language=sr_lang)
        except sr.UnknownValueError:
            return {
                "transcript": "",
                "language": lang,
                "confidence": 0.0,
                "words": [],
                "source": "google_fallback",
                "error": "Could not understand audio"
            }
        except sr.RequestError as e:
            raise Exception(f"Google Speech API error: {e}")

        # Build simple word list
        words = []
        for i, word in enumerate(transcript.split()):
            words.append({
                "word": word,
                "start": i * 0.3,
                "end": (i + 1) * 0.3
            })

        return {
            "transcript": transcript,
            "language": lang,
            "confidence": 0.82,
            "words": words,
            "source": "google_fallback"
        }

    def _ensure_wav(self, audio_path: str) -> str:
        """Convert audio to WAV format if it isn't already."""
        if audio_path.lower().endswith('.wav'):
            return audio_path
        
        # Try ffmpeg conversion
        try:
            import subprocess
            wav_path = audio_path.rsplit('.', 1)[0] + '_converted.wav'
            subprocess.run(
                ['ffmpeg', '-i', audio_path, '-ar', '16000', '-ac', '1', wav_path, '-y'],
                capture_output=True, timeout=10
            )
            if os.path.exists(wav_path):
                return wav_path
        except Exception:
            pass
        
        # If we can't convert, return original and hope for the best
        return audio_path

    def transcribe_text(self, text: str, language: Optional[str] = None) -> Dict[str, Any]:
        """
        Direct text passthrough — for manual text input mode.
        Used when microphone is unavailable or for testing.
        """
        lang = language or self.language
        words = [
            {"word": w, "start": i * 0.3, "end": (i + 1) * 0.3}
            for i, w in enumerate(text.split())
        ]
        return {
            "transcript": text,
            "language": lang,
            "confidence": 1.0,
            "words": words,
            "source": "manual"
        }

