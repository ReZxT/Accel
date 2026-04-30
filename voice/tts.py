import subprocess
import tempfile
import os
import scipy.io.wavfile as wav
import numpy as np

PIPER_BIN = os.path.join(os.path.dirname(__file__), "models/piper/piper/piper")
PIPER_MODEL = os.path.join(os.path.dirname(__file__), "models/piper/en_US-lessac-medium.onnx")


def speak(text: str):
    """Synthesize text with piper and play through system audio."""
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        tmp_path = f.name

    try:
        subprocess.run(
            [PIPER_BIN, "--model", PIPER_MODEL, "--output_file", tmp_path],
            input=text.encode(),
            check=True,
            capture_output=True,
        )
        import sounddevice as sd
        rate, data = wav.read(tmp_path)
        if data.dtype == np.int16:
            data = data.astype(np.float32) / 32768.0
        sd.play(data, rate)
        sd.wait()
    finally:
        os.unlink(tmp_path)
