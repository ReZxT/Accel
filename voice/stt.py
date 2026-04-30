import numpy as np
from faster_whisper import WhisperModel

_model = None

def _get_model() -> WhisperModel:
    global _model
    if _model is None:
        # base model — good accuracy/speed balance on CPU, handles Polish + English
        _model = WhisperModel("base", device="cpu", compute_type="int8")
    return _model


def transcribe(audio: np.ndarray, sample_rate: int = 16000) -> str:
    """Transcribe audio array to text. Returns empty string if nothing detected."""
    model = _get_model()
    # faster-whisper expects float32 mono at 16kHz
    if audio.dtype != np.float32:
        audio = audio.astype(np.float32)
    if audio.ndim > 1:
        audio = audio.mean(axis=1)
    if sample_rate != 16000:
        import scipy.signal as signal
        audio = signal.resample(audio, int(len(audio) * 16000 / sample_rate))

    segments, _ = model.transcribe(audio, beam_size=5, language=None)
    return " ".join(s.text.strip() for s in segments).strip()
