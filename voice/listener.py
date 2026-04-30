import numpy as np
import threading
import queue
import os
from openwakeword.model import Model

WAKEWORD_MODEL = os.path.join(
    os.path.dirname(__file__),
    "../.venv/lib/python3.12/site-packages/openwakeword/resources/models/hey_jarvis_v0.1.onnx"
)
SAMPLE_RATE = 16000
CHUNK_MS = 80          # openWakeWord expects 80ms chunks at 16kHz = 1280 frames
CHUNK_FRAMES = int(SAMPLE_RATE * CHUNK_MS / 1000)
VAD_SILENCE_SEC = 1.2  # stop recording after this much silence post-speech
VAD_THRESHOLD = 0.5    # openWakeWord's built-in Silero VAD threshold
WAKEWORD_THRESHOLD = 0.5
MAX_RECORD_SEC = 30


def record_utterance() -> np.ndarray:
    """Record until VAD detects speech then silence. Returns float32 mono array."""
    import sounddevice as sd
    vad_model = Model(
        wakeword_model_paths=[WAKEWORD_MODEL],
        vad_threshold=VAD_THRESHOLD,
    )
    frames = []
    silence_frames = 0
    speech_started = False
    silence_limit = int(VAD_SILENCE_SEC * SAMPLE_RATE / CHUNK_FRAMES)
    max_frames = int(MAX_RECORD_SEC * SAMPLE_RATE / CHUNK_FRAMES)

    with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="float32",
                        blocksize=CHUNK_FRAMES) as stream:
        for _ in range(max_frames):
            chunk, _ = stream.read(CHUNK_FRAMES)
            chunk_mono = chunk[:, 0]
            frames.append(chunk_mono.copy())
            vad_model.predict(chunk_mono)
            vad_score = vad_model.vad[-1] if vad_model.vad else 0.0

            if vad_score > VAD_THRESHOLD:
                speech_started = True
                silence_frames = 0
            elif speech_started:
                silence_frames += 1
                if silence_frames >= silence_limit:
                    break

    return np.concatenate(frames) if frames else np.array([], dtype=np.float32)


class WakeWordListener:
    """Continuously listens for the wake word in a background thread."""

    def __init__(self, on_triggered):
        self._on_triggered = on_triggered
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._oww: Model | None = None

    def start(self):
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=3)

    def _run(self):
        self._oww = Model(
            wakeword_model_paths=[WAKEWORD_MODEL],
            vad_threshold=0.0,  # VAD handled separately in record_utterance
        )
        q: queue.Queue = queue.Queue()

        def _cb(indata, frames, time_info, status):
            q.put(indata[:, 0].copy())

        import sounddevice as sd
        with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="float32",
                            blocksize=CHUNK_FRAMES, callback=_cb):
            while not self._stop.is_set():
                try:
                    chunk = q.get(timeout=0.5)
                except queue.Empty:
                    continue
                preds = self._oww.predict(chunk)
                score = max(preds.values()) if preds else 0.0
                if score >= WAKEWORD_THRESHOLD:
                    # drain queue to avoid stale audio
                    while not q.empty():
                        q.get_nowait()
                    self._oww.reset()
                    self._on_triggered()
