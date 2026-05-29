"""Spectral analysis for the web API (scipy-only, no librosa)."""

from __future__ import annotations

from typing import Any, Dict, Optional

import numpy as np
from scipy import signal
from scipy.stats import entropy


def analyze_waveform(
    waveform: np.ndarray,
    sample_rate: int,
    prob_dist: Optional[Any] = None,
) -> Dict[str, float]:
    """Match desktop SpectralAnalyzer.analyze() metrics used in the GUI report."""
    if waveform.ndim > 1:
        waveform = np.mean(waveform, axis=1)

    results: Dict[str, float] = {}
    results.update(_compute_spectral_features(waveform, sample_rate))
    results.update(_compute_non_stationarity(waveform, sample_rate))
    results.update(_compute_modulation_characteristics(waveform, sample_rate))
    results.update(_compute_quantum_indicators(waveform, sample_rate, prob_dist))
    return results


def format_analysis_report(results: Dict[str, float]) -> str:
    """Formatted text matching qwave/gui/main_window.py display_analysis()."""
    lines = [
      "=" * 50,
      "QUANTUM AUDIO SPECTRAL ANALYSIS",
      "=" * 50,
      "",
      "--- Basic Spectral Features ---",
      f"Spectral Centroid:      {results.get('spectral_centroid_hz', 0):.2f} Hz",
      f"Spectral Bandwidth:     {results.get('spectral_bandwidth_hz', 0):.2f} Hz",
      f"Spectral Rolloff:       {results.get('spectral_rolloff_hz', 0):.2f} Hz",
      "",
      "--- Non-Stationarity Analysis ---",
      f"Non-Stationarity Index: {results.get('non_stationarity_index', 0):.4f}",
      f"Temporal Variation:     {results.get('temporal_variation', 0):.4f}",
      "",
      "--- Modulation Characteristics ---",
      f"Modulation Depth:              {results.get('modulation_depth', 0):.4f}",
      f"Frequency Modulation Index:    {results.get('frequency_modulation_index', 0):.4f}",
      f"Avg Spectral Spread:           {results.get('average_spectral_spread_hz', 0):.2f} Hz",
      f"Spectral Spread Variation:     {results.get('spectral_spread_variation', 0):.4f}",
      "",
      "--- Quantum Pattern Indicators ---",
      f"Spectral Entropy:       {results.get('spectral_entropy', 0):.4f}",
    ]
    return "\n".join(lines)


def _compute_spectral_features(waveform: np.ndarray, sample_rate: int) -> Dict[str, float]:
    frequencies, psd = signal.welch(
        waveform,
        sample_rate,
        nperseg=min(2048, max(4, len(waveform) // 4)),
    )
    total = float(np.sum(psd)) or 1.0
    spectral_centroid = float(np.sum(frequencies * psd) / total)
    spectral_bandwidth = float(
        np.sqrt(np.sum(((frequencies - spectral_centroid) ** 2) * psd) / total)
    )
    cumsum_psd = np.cumsum(psd)
    rolloff_index = np.where(cumsum_psd >= 0.85 * cumsum_psd[-1])[0]
    spectral_rolloff = (
        float(frequencies[rolloff_index[0]])
        if len(rolloff_index) > 0
        else float(frequencies[-1]) if len(frequencies) > 0 else 0.0
    )
    geometric_mean = np.exp(np.mean(np.log(psd + 1e-10)))
    arithmetic_mean = np.mean(psd)
    spectral_flatness = float(geometric_mean / (arithmetic_mean + 1e-10))
    return {
        "spectral_centroid_hz": spectral_centroid,
        "spectral_bandwidth_hz": spectral_bandwidth,
        "spectral_rolloff_hz": spectral_rolloff,
        "spectral_flatness": spectral_flatness,
    }


def _compute_non_stationarity(waveform: np.ndarray, sample_rate: int) -> Dict[str, float]:
    segment_length = min(2048, max(1, len(waveform) // 10))
    num_segments = len(waveform) // segment_length
    if num_segments < 2:
        return {"non_stationarity_index": 0.0, "temporal_variation": 0.0}

    segment_centroids = []
    for i in range(num_segments):
        segment = waveform[i * segment_length : (i + 1) * segment_length]
        if len(segment) > 0:
            freqs, psd = signal.welch(segment, sample_rate, nperseg=min(512, len(segment)))
            if np.sum(psd) > 0:
                segment_centroids.append(float(np.sum(freqs * psd) / np.sum(psd)))

    if len(segment_centroids) < 2:
        return {"non_stationarity_index": 0.0, "temporal_variation": 0.0}

    mean_centroid = np.mean(segment_centroids)
    std_centroid = np.std(segment_centroids)
    non_stationarity_index = float(std_centroid / (mean_centroid + 1e-10))
    temporal_variation = float(
        np.var(segment_centroids) / (np.mean(np.abs(segment_centroids)) + 1e-10)
    )
    return {
        "non_stationarity_index": non_stationarity_index,
        "temporal_variation": temporal_variation,
    }


def _compute_modulation_characteristics(waveform: np.ndarray, sample_rate: int) -> Dict[str, float]:
    analytic_signal = signal.hilbert(waveform)
    envelope = np.abs(analytic_signal)
    instantaneous_phase = np.unwrap(np.angle(analytic_signal))
    instantaneous_frequency = np.diff(instantaneous_phase) / (2.0 * np.pi) * sample_rate

    modulation_depth = float(np.std(envelope) / (np.mean(envelope) + 1e-10))
    if len(instantaneous_frequency) > 0:
        freq_modulation_index = float(
            np.std(instantaneous_frequency)
            / (np.mean(np.abs(instantaneous_frequency)) + 1e-10)
        )
    else:
        freq_modulation_index = 0.0

    hop_length = 512
    n_fft = 2048
    freqs, _times, stft = signal.stft(
        waveform,
        fs=sample_rate,
        nperseg=n_fft,
        noverlap=n_fft - hop_length,
    )
    magnitude = np.abs(stft)

    spectral_spreads = []
    for t in range(magnitude.shape[1]):
        frame = magnitude[:, t]
        if np.sum(frame) > 0:
            centroid = np.sum(freqs * frame) / np.sum(frame)
            spread = np.sqrt(np.sum(((freqs - centroid) ** 2) * frame) / np.sum(frame))
            spectral_spreads.append(float(spread))

    avg_spectral_spread = float(np.mean(spectral_spreads)) if spectral_spreads else 0.0
    spectral_spread_variation = float(np.std(spectral_spreads)) if spectral_spreads else 0.0
    return {
        "modulation_depth": modulation_depth,
        "frequency_modulation_index": freq_modulation_index,
        "average_spectral_spread_hz": avg_spectral_spread,
        "spectral_spread_variation": spectral_spread_variation,
    }


def _compute_mutual_information(prob_dist: Any) -> float:
    if prob_dist is None:
        return 0.0

    if hasattr(prob_dist, "tolist"):
        arr = np.asarray(prob_dist, dtype=float).flatten()
        normalized_prob_dist = {format(i, f"0{int(np.log2(len(arr)))}b"): p for i, p in enumerate(arr) if p > 0}
    elif isinstance(prob_dist, dict):
        normalized_prob_dist = {str(k): float(v) for k, v in prob_dist.items() if float(v) > 0}
    else:
        return 0.0

    prob_A: Dict[str, float] = {}
    prob_B: Dict[str, float] = {}
    for bitstring, prob in normalized_prob_dist.items():
        state = str(bitstring)
        mid = len(state) // 2
        part_A = state[:mid]
        part_B = state[mid:]
        prob_A[part_A] = prob_A.get(part_A, 0.0) + prob
        prob_B[part_B] = prob_B.get(part_B, 0.0) + prob

    def shannon_entropy(p_dict: Dict[str, float]) -> float:
        return float(-sum(p * np.log2(p) for p in p_dict.values() if p > 0))

    h_A = shannon_entropy(prob_A)
    h_B = shannon_entropy(prob_B)
    h_AB = shannon_entropy(normalized_prob_dist)
    return max(0.0, h_A + h_B - h_AB)


def _compute_quantum_indicators(
    waveform: np.ndarray,
    sample_rate: int,
    prob_dist: Optional[Any],
) -> Dict[str, float]:
    _frequencies, psd = signal.welch(
        waveform,
        sample_rate,
        nperseg=min(2048, max(4, len(waveform) // 4)),
    )
    psd_normalized = psd / (np.sum(psd) + 1e-10)
    n_bins = len(psd_normalized)
    if n_bins > 1:
        spectral_entropy = float(entropy(psd_normalized + 1e-10) / np.log(n_bins))
    else:
        spectral_entropy = 0.0
    mutual_info = _compute_mutual_information(prob_dist)
    return {
        "spectral_entropy": spectral_entropy,
        "mutual_information": mutual_info,
        "quantum_likelihood_score": spectral_entropy * (mutual_info + 1.0),
    }


def compute_spectrum_preview(
    waveform: np.ndarray,
    sample_rate: int,
    max_points: int = 512,
) -> Dict[str, list]:
    """Downsampled magnitude spectrum for the web waveform panel (dB)."""
    if waveform.ndim > 1:
        waveform = np.mean(waveform, axis=1)
    freq_axis = np.fft.rfftfreq(len(waveform), d=1 / sample_rate)
    spectrum = np.abs(np.fft.rfft(waveform))
    spectrum_db = 20 * np.log10(spectrum + 1e-9)

    power = spectrum ** 2
    total_power = float(np.sum(power))
    if total_power > 0:
        cumulative = np.cumsum(power) / total_power
        cutoff_idx = int(np.searchsorted(cumulative, 0.995))
        cutoff_idx = min(max(cutoff_idx, 1), len(freq_axis) - 1)
        max_freq = max(1000.0, min(float(freq_axis[cutoff_idx]) * 1.1, float(freq_axis[-1])))
    else:
        max_freq = min(10000.0, float(freq_axis[-1]))

    mask = freq_axis <= max_freq
    freq_axis = freq_axis[mask]
    spectrum_db = spectrum_db[mask]

    if len(freq_axis) > max_points:
        indices = np.linspace(0, len(freq_axis) - 1, max_points, dtype=int)
        freq_axis = freq_axis[indices]
        spectrum_db = spectrum_db[indices]

    return {
        "frequencies_hz": freq_axis.astype(float).tolist(),
        "magnitude_db": spectrum_db.astype(float).tolist(),
    }
