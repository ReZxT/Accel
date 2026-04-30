"""
Voice pipeline: wake word → STT → chat → TTS.
Runs as a background thread. Enabled/disabled via VoicePipeline.start()/stop().
"""
import asyncio
import json
import logging
import threading
import httpx

from .listener import WakeWordListener, record_utterance
from .stt import transcribe
from .tts import speak
from .filter import filter_response, tool_phrase

log = logging.getLogger(__name__)

CHAT_URL = "http://localhost:8100/chat"
SESSION_ID = "voice-default"


class VoicePipeline:
    def __init__(self):
        self._listener = WakeWordListener(on_triggered=self._on_wake)
        self._busy = threading.Lock()
        self.enabled = False

    def start(self):
        self.enabled = True
        self._listener.start()
        log.info("Voice pipeline started — say 'Hey Jarvis' to activate")

    def stop(self):
        self.enabled = False
        self._listener.stop()
        log.info("Voice pipeline stopped")

    def _on_wake(self):
        """Called from listener thread when wake word detected."""
        if not self._busy.acquire(blocking=False):
            return  # already processing
        try:
            speak("Yes?")
            audio = record_utterance()
            if audio is None or len(audio) < 1600:  # < 0.1s — probably silence
                return

            text = transcribe(audio)
            if not text:
                speak("Sorry, I didn't catch that.")
                return

            log.info(f"Voice input: {text!r}")
            response = self._send_to_chat(text)
            if response:
                speak(filter_response(response))
        except Exception as e:
            log.error(f"Voice pipeline error: {e}")
            speak("Something went wrong.")
        finally:
            self._busy.release()

    def _send_to_chat(self, text: str) -> str:
        """Send text to /chat SSE endpoint, collect response text, speak tool status lines."""
        payload = {
            "chatInput": text,
            "sessionId": SESSION_ID,
            "chatHistory": [],
            "voice_mode": True,
        }
        response_chunks = []
        spoken_tools: set = set()
        try:
            with httpx.Client(timeout=120) as client:
                with client.stream("POST", CHAT_URL, json=payload) as resp:
                    for line in resp.iter_lines():
                        if not line.startswith("data: "):
                            continue
                        try:
                            event = json.loads(line[6:])
                        except json.JSONDecodeError:
                            continue

                        etype = event.get("type")
                        if etype == "tool_call":
                            tool = event.get("tool", "")
                            # Only speak status once per tool per turn
                            if tool not in spoken_tools:
                                spoken_tools.add(tool)
                                speak(tool_phrase(tool))
                        elif etype == "text":
                            response_chunks.append(event.get("text", ""))
        except Exception as e:
            log.error(f"Chat request failed: {e}")
        return "".join(response_chunks)


# Singleton
_pipeline = VoicePipeline()


def get_pipeline() -> VoicePipeline:
    return _pipeline
