"""Shared audio generation pipeline for the Musiq web API."""

from __future__ import annotations

import base64
import io
from typing import Any, Callable, Dict, List, Optional

import numpy as np
from scipy.fft import fft, fftfreq
from scipy.stats import entropy

from qwave.modules.generator import AudioGenerator
from qwave.utils.backends import BACKEND_AER, BACKEND_IONQ_QPU, BACKEND_IONQ_SIMULATOR, parse_backend_type
from qwave.web.circuit_json import circuit_from_payload
from qwave.web.simulator_light import simulate_ideal


StatusCallback = Optional[Callable[[str], None]]

IONQ_BACKENDS = {BACKEND_IONQ_SIMULATOR, BACKEND_IONQ_QPU}


def _encode_wav_base64(waveform: np.ndarray, sample_rate: int) -> str:
    import soundfile as sf

    buffer = io.BytesIO()
    sf.write(buffer, waveform, sample_rate, format="WAV")
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def _downsample_waveform(waveform: np.ndarray, max_points: int = 2000) -> List[float]:
    if len(waveform) <= max_points:
        return waveform.astype(float).tolist()
    indices = np.linspace(0, len(waveform) - 1, max_points, dtype=int)
    return waveform[indices].astype(float).tolist()


def _fallback_metrics(waveform: np.ndarray, sample_rate: int) -> Dict[str, float]:
    spectrum = np.abs(fft(waveform))
    freqs = fftfreq(len(waveform), 1 / sample_rate)
    positive = freqs >= 0
    spectrum = spectrum[positive]
    freqs = freqs[positive]
    total = float(np.sum(spectrum)) or 1.0
    centroid = float(np.sum(freqs * spectrum) / total)
    spread = float(np.sqrt(np.sum(((freqs - centroid) ** 2) * spectrum) / total))
    normalized = spectrum / total
    spectral_entropy = float(entropy(normalized + 1e-12))
    return {
        "spectral_centroid_hz": centroid,
        "spectral_bandwidth_hz": spread,
        "spectral_entropy": spectral_entropy,
        "non_stationarity_index": float(np.std(waveform)),
    }


def generate_audio_from_payload(
    payload: Dict[str, Any],
    status_callback: StatusCallback = None,
) -> Dict[str, Any]:
    duration = float(payload.get("duration", 2.0))
    sample_rate = int(payload.get("sample_rate", 44100))
    shots = int(payload.get("shots", 1024))
    backend_type = parse_backend_type(payload.get("backend", BACKEND_AER))

    circuit = circuit_from_payload(payload)
    if circuit.size() == 0:
        raise ValueError("Circuit is empty. Add at least one gate before generating audio.")

    logs: List[str] = []
    warning = None

    def emit(message: str) -> None:
        logs.append(message)
        if status_callback is not None:
            status_callback(message)

    if backend_type in IONQ_BACKENDS:
        warning = (
            "IonQ backends are not available in the web deployment yet. "
            "Using local ideal simulation instead."
        )
        emit(f"Warning: {warning}")

    emit("Execution backend: Local Ideal Simulator")
    emit("Running quantum simulation...")
    statevector, measurement_sequence, probability_dist = simulate_ideal(circuit, shots)
    status = {
        "requested": backend_type,
        "effective": BACKEND_AER,
        "effective_label": "Local Ideal Simulator",
        "warning": warning,
    }

    emit(f"Simulation completed: {len(measurement_sequence)} outcomes")
    emit("Generating audio waveform...")

    generator = AudioGenerator(sample_rate=sample_rate)
    waveform = generator.map_quantum_to_audio(
        statevector=statevector,
        measurement_sequence=measurement_sequence,
        probability_distribution=probability_dist,
        duration=duration,
        apply_envelope=True,
        apply_reverb=False,
    )

    analysis = _fallback_metrics(waveform, sample_rate)

    return {
        "audio_base64": _encode_wav_base64(waveform, sample_rate),
        "sample_rate": sample_rate,
        "duration": duration,
        "waveform_preview": _downsample_waveform(waveform),
        "analysis": analysis,
        "backend": status,
        "logs": logs,
        "measurement_outcomes": len(measurement_sequence),
    }
