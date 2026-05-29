"""Shared audio generation pipeline for the Musiq web API."""

from __future__ import annotations

import base64
import io
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

import numpy as np
from qwave.modules.generator import AudioGenerator
from qwave.utils.backends import (
    BACKEND_AER,
    BACKEND_IONQ_QPU,
    BACKEND_IONQ_SIMULATOR,
    get_backend_label,
    parse_backend_type,
)
from qwave.web.circuit_json import circuit_from_payload
from qwave.web.ionq_runner import resolve_ionq_backend, run_ionq_shots
from qwave.web.simulator_light import simulate_ideal
from qwave.web.spectral_analysis import (
    analyze_waveform,
    compute_spectrum_preview,
    format_analysis_report,
)


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


def _probability_distribution_from_counts(
    counts: Dict[str, int],
    num_qubits: int,
    shots: int,
) -> np.ndarray:
    num_states = 2 ** num_qubits
    probabilities = np.zeros(num_states)
    for bitstring, count in counts.items():
        probabilities[int(bitstring, 2)] = count / shots
    return probabilities


def _measurement_sequence_from_probabilities(probabilities: np.ndarray, shots: int) -> List[int]:
    return np.random.choice(len(probabilities), size=shots, p=probabilities).tolist()


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
    warning: Optional[str] = None

    def emit(message: str) -> None:
        logs.append(message)
        if status_callback is not None:
            status_callback(message)

    effective_type, warning, effective_label = resolve_ionq_backend(backend_type)
    if warning:
        emit(f"Warning: {warning}")
        emit("Falling back to Local Ideal Simulator.")

    emit(f"Execution backend: {effective_label}")

    use_ionq = effective_type in IONQ_BACKENDS

    if use_ionq:
        emit("Computing statevector locally (ideal); measurement shots use IonQ.")
        statevector, _, _ = simulate_ideal(circuit, shots)
        emit("Running quantum simulation on IonQ...")
        counts = run_ionq_shots(circuit, shots, effective_type, status_callback=emit)
        probability_dist = _probability_distribution_from_counts(counts, circuit.num_qubits, shots)
        measurement_sequence = _measurement_sequence_from_probabilities(probability_dist, shots)
    else:
        emit("Running quantum simulation...")
        statevector, measurement_sequence, probability_dist = simulate_ideal(circuit, shots)

    status = {
        "requested": backend_type,
        "effective": effective_type,
        "requested_label": get_backend_label(backend_type, web=True),
        "effective_label": effective_label,
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

    emit("Performing spectral analysis...")
    prob_for_analysis = probability_dist
    if hasattr(prob_for_analysis, "tolist"):
        prob_for_analysis = prob_for_analysis.tolist()
    analysis = analyze_waveform(waveform, sample_rate, prob_dist=prob_for_analysis)
    analysis_report = format_analysis_report(analysis)
    spectrum_preview = compute_spectrum_preview(waveform, sample_rate)

    return {
        "audio_base64": _encode_wav_base64(waveform, sample_rate),
        "sample_rate": sample_rate,
        "duration": duration,
        "waveform_preview": _downsample_waveform(waveform),
        "spectrum_preview": spectrum_preview,
        "analysis": analysis,
        "analysis_report": analysis_report,
        "backend": status,
        "logs": logs,
        "measurement_outcomes": len(measurement_sequence),
        "saved_audio_filename": f"qwave_{datetime.now().strftime('%Y%m%d_%H%M%S')}.wav",
    }
