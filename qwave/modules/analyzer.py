"""
Spectral Analysis Module

This module performs spectral analysis on generated audio to detect and quantify
non-classical audio patterns, such as non-stationarity and quantum interference effects.
"""

import numpy as np
import librosa
import soundfile as sf
from typing import Dict, Tuple, Optional
from scipy import signal
from scipy.stats import entropy
from scipy.fft import fft, fftfreq

from qwave.utils.constants import SAMPLING_RATE


class SpectralAnalyzer:
    """
    Analyzes audio waveforms to detect non-classical patterns.
    
    This class implements various spectral analysis techniques to identify
    characteristics that distinguish quantum-generated audio from classical
    noise or random audio patterns.
    """
    
    def __init__(self, sample_rate: int = SAMPLING_RATE):
        """
        Initialize the spectral analyzer.
        
        Args:
            sample_rate: Audio sample rate in Hz (default: 44100)
        """
        self.sample_rate = sample_rate
    
    def analyze(self, waveform: np.ndarray, prob_dist: Optional[dict] = None) -> Dict[str, float]:
        """
        Perform comprehensive spectral analysis on the audio waveform.
        
        Args:
            waveform: Audio waveform array
            prob_dist: Optional probability distribution from quantum simulation
            
        Returns:
            Dictionary containing various spectral metrics
        """
        results = {}
        
        # Basic spectral features
        results.update(self._compute_spectral_features(waveform))
        
        # Non-stationarity analysis
        results.update(self._compute_non_stationarity(waveform))
        
        # Modulation characteristics
        results.update(self._compute_modulation_characteristics(waveform))
        
        # Quantum interference indicators
        results.update(self._compute_quantum_indicators(waveform, prob_dist))
        
        return results
    
    def load_audio(self, filepath: str) -> Tuple[np.ndarray, int]:
        """
        Load audio file
        
        Args:
            filepath: Audio file path
            
        Returns:
            (waveform data, sampling frequency)
        """
        waveform, sr = sf.read(filepath)
        
        # Convert to mono
        if len(waveform.shape) > 1:
            waveform = np.mean(waveform, axis=1)
        
        # Normalize
        if np.max(np.abs(waveform)) > 0:
            waveform = waveform / np.max(np.abs(waveform))
        
        return waveform, sr
    
    def compute_spectrogram(
        self, 
        waveform: np.ndarray,
        n_fft: int = 2048,
        hop_length: int = 512,
        win_length: Optional[int] = None
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Compute spectrogram
        
        Args:
            waveform: Waveform data
            n_fft: FFT window size
            hop_length: Hop size
            win_length: Window size
            
        Returns:
            (spectrogram, time axis, frequency axis)
        """
        # Short-time Fourier transform
        S = librosa.stft(
            waveform,
            n_fft=n_fft,
            hop_length=hop_length,
            win_length=win_length
        )
        
        # Power spectrogram
        magnitude = np.abs(S) ** 2
        
        # Convert to decibels
        spectrogram_db = librosa.power_to_db(magnitude, ref=np.max)
        
        # Time axis
        times = librosa.frames_to_time(
            np.arange(S.shape[1]),
            sr=self.sample_rate,
            hop_length=hop_length
        )
        
        # Frequency axis
        frequencies = librosa.fft_frequencies(sr=self.sample_rate, n_fft=n_fft)
        
        return spectrogram_db, times, frequencies
    
    def analyze_audio_features(self, waveform: np.ndarray) -> Dict[str, float]:
        """
        Analyze audio features (compatibility method)
        
        Args:
            waveform: Waveform data
            
        Returns:
            Feature dictionary
        """
        # Use the main analyze method and map to expected feature names
        results = self.analyze(waveform)
        
        # Map to expected feature names for compatibility
        features = {
            'spectral_entropy': results.get('spectral_entropy', 0.0),
            'spectral_centroid': results.get('spectral_centroid_hz', 0.0),
            'spectral_rolloff': results.get('spectral_rolloff_hz', 0.0),
            'temporal_modulation': results.get('temporal_variation', 0.0),
            'zero_crossing_rate': self._compute_zero_crossing_rate(waveform),
            'fundamental_frequency': self._compute_fundamental_frequency(waveform),
            'scale_invariance': self._compute_scale_invariance(waveform)
        }
        
        return features
    
    def _compute_spectral_features(self, waveform: np.ndarray) -> Dict[str, float]:
        """
        Compute basic spectral features.
        
        Args:
            waveform: Audio waveform array
            
        Returns:
            Dictionary of spectral features
        """
        # Compute power spectral density
        frequencies, psd = signal.welch(
            waveform,
            self.sample_rate,
            nperseg=min(2048, len(waveform) // 4)
        )
        
        # Spectral centroid (brightness)
        spectral_centroid = np.sum(frequencies * psd) / np.sum(psd) if np.sum(psd) > 0 else 0.0
        
        # Spectral bandwidth
        spectral_bandwidth = np.sqrt(
            np.sum(((frequencies - spectral_centroid) ** 2) * psd) / np.sum(psd)
        ) if np.sum(psd) > 0 else 0.0
        
        # Spectral rolloff (frequency below which 85% of energy is contained)
        cumsum_psd = np.cumsum(psd)
        rolloff_index = np.where(cumsum_psd >= 0.85 * cumsum_psd[-1])[0] if len(cumsum_psd) > 0 else []
        spectral_rolloff = frequencies[rolloff_index[0]] if len(rolloff_index) > 0 else frequencies[-1] if len(frequencies) > 0 else 0.0
        
        # Spectral flatness (measure of noisiness)
        geometric_mean = np.exp(np.mean(np.log(psd + 1e-10)))
        arithmetic_mean = np.mean(psd)
        spectral_flatness = geometric_mean / (arithmetic_mean + 1e-10)
        
        return {
            'spectral_centroid_hz': spectral_centroid,
            'spectral_bandwidth_hz': spectral_bandwidth,
            'spectral_rolloff_hz': spectral_rolloff,
            'spectral_flatness': spectral_flatness
        }
    
    def _compute_non_stationarity(self, waveform: np.ndarray) -> Dict[str, float]:
        """
        Compute non-stationarity metrics.
        
        Quantum interference patterns should exhibit non-stationary characteristics
        that differ from classical random noise.
        
        Args:
            waveform: Audio waveform array
            
        Returns:
            Dictionary of non-stationarity metrics
        """
        # Divide waveform into segments
        segment_length = min(2048, len(waveform) // 10)
        num_segments = len(waveform) // segment_length
        
        if num_segments < 2:
            return {
                'non_stationarity_index': 0.0,
                'temporal_variation': 0.0
            }
        
        # Compute spectral centroid for each segment
        segment_centroids = []
        for i in range(num_segments):
            segment = waveform[i * segment_length:(i + 1) * segment_length]
            if len(segment) > 0:
                freqs, psd = signal.welch(segment, self.sample_rate, nperseg=min(512, len(segment)))
                if np.sum(psd) > 0:
                    centroid = np.sum(freqs * psd) / np.sum(psd)
                    segment_centroids.append(centroid)
        
        if len(segment_centroids) < 2:
            return {
                'non_stationarity_index': 0.0,
                'temporal_variation': 0.0
            }
        
        # Non-stationarity index: coefficient of variation of spectral centroids
        mean_centroid = np.mean(segment_centroids)
        std_centroid = np.std(segment_centroids)
        non_stationarity_index = std_centroid / (mean_centroid + 1e-10)
        
        # Temporal variation: normalized variance
        temporal_variation = np.var(segment_centroids) / (np.mean(np.abs(segment_centroids)) + 1e-10)
        
        return {
            'non_stationarity_index': non_stationarity_index,
            'temporal_variation': temporal_variation
        }
    
    def _compute_modulation_characteristics(self, waveform: np.ndarray) -> Dict[str, float]:
        """
        Compute modulation characteristics.
        
        Quantum interference should create specific modulation patterns
        that differ from classical signals.
        
        Args:
            waveform: Audio waveform array
            
        Returns:
            Dictionary of modulation metrics
        """
        # Compute envelope (amplitude modulation)
        analytic_signal = signal.hilbert(waveform)
        envelope = np.abs(analytic_signal)
        
        # Compute instantaneous phase
        instantaneous_phase = np.unwrap(np.angle(analytic_signal))
        instantaneous_frequency = np.diff(instantaneous_phase) / (2.0 * np.pi) * self.sample_rate
        
        # Modulation depth (variance of envelope)
        modulation_depth = np.std(envelope) / (np.mean(envelope) + 1e-10)
        
        # Frequency modulation index (variance of instantaneous frequency)
        if len(instantaneous_frequency) > 0:
            freq_modulation_index = np.std(instantaneous_frequency) / (np.mean(np.abs(instantaneous_frequency)) + 1e-10)
        else:
            freq_modulation_index = 0.0
        
        # Spectral spread (measure of frequency spread over time)
        # Compute spectrogram
        hop_length = 512
        n_fft = 2048
        stft = librosa.stft(waveform, hop_length=hop_length, n_fft=n_fft)
        magnitude = np.abs(stft)
        
        # Compute spectral spread for each time frame
        freqs = librosa.fft_frequencies(sr=self.sample_rate, n_fft=n_fft)
        spectral_spreads = []
        for t in range(magnitude.shape[1]):
            frame = magnitude[:, t]
            if np.sum(frame) > 0:
                centroid = np.sum(freqs * frame) / np.sum(frame)
                spread = np.sqrt(np.sum(((freqs - centroid) ** 2) * frame) / np.sum(frame))
                spectral_spreads.append(spread)
        
        avg_spectral_spread = np.mean(spectral_spreads) if spectral_spreads else 0.0
        spectral_spread_variation = np.std(spectral_spreads) if spectral_spreads else 0.0
        
        return {
            'modulation_depth': modulation_depth,
            'frequency_modulation_index': freq_modulation_index,
            'average_spectral_spread_hz': avg_spectral_spread,
            'spectral_spread_variation': spectral_spread_variation
        }
    
    def _compute_mutual_information(self, prob_dist) -> float:
        """Calculate mutual information by splitting bitstrings into two halves."""
        if prob_dist is None:
            return 0.0

        prob_A = {}
        prob_B = {}
        normalized_prob_dist = {}

        # Accept both dict[str, float] and ndarray probabilities from simulator.
        if isinstance(prob_dist, dict):
            items = prob_dist.items()
        else:
            probs = np.asarray(prob_dist, dtype=float).ravel()
            if probs.size == 0:
                return 0.0
            n_qubits = int(np.ceil(np.log2(probs.size))) if probs.size > 1 else 1
            items = (
                (format(i, f"0{n_qubits}b"), p)
                for i, p in enumerate(probs)
            )

        for bitstring, prob in items:
            state = str(bitstring)
            p = float(prob)
            if p <= 0:
                continue
            mid = len(state) // 2
            part_A = state[:mid]
            part_B = state[mid:]

            prob_A[part_A] = prob_A.get(part_A, 0.0) + p
            prob_B[part_B] = prob_B.get(part_B, 0.0) + p
            normalized_prob_dist[state] = normalized_prob_dist.get(state, 0.0) + p

        def shannon_entropy(p_dict: dict) -> float:
            return float(-sum(p * np.log2(p) for p in p_dict.values() if p > 0))

        h_A = shannon_entropy(prob_A)
        h_B = shannon_entropy(prob_B)
        h_AB = shannon_entropy(normalized_prob_dist)

        # Mutual Information: I(A;B) = H(A) + H(B) - H(A,B)
        return max(0.0, h_A + h_B - h_AB)

    def _compute_quantum_indicators(self, waveform: np.ndarray, prob_dist: Optional[dict] = None) -> Dict[str, float]:
        """
        Compute indicators specific to quantum-generated audio.
        
        These metrics attempt to capture characteristics that might indicate
        quantum interference patterns.
        
        Args:
            waveform: Audio waveform array
            prob_dist: Optional probability distribution from quantum simulation
            
        Returns:
            Dictionary of quantum-specific metrics
        """
        # Compute power spectral density
        _frequencies, psd = signal.welch(
            waveform,
            self.sample_rate,
            nperseg=min(2048, len(waveform) // 4)
        )
        
        # Normalize PSD
        psd_normalized = psd / (np.sum(psd) + 1e-10)
        
        # Spectral entropy (measure of spectral complexity)
        # Higher entropy suggests more complex, potentially quantum-like patterns
        spectral_entropy = float(entropy(psd_normalized + 1e-10))
        mutual_info = self._compute_mutual_information(prob_dist) if prob_dist is not None else 0.0

        return {
            'spectral_entropy': spectral_entropy,
            'mutual_information': mutual_info,
            'quantum_likelihood_score': spectral_entropy * (mutual_info + 1.0)
        }
    
    def _compute_zero_crossing_rate(self, waveform: np.ndarray) -> float:
        """Compute zero crossing rate."""
        return float(np.mean(librosa.feature.zero_crossing_rate(waveform)))
    
    def _compute_fundamental_frequency(self, waveform: np.ndarray) -> float:
        """Compute fundamental frequency."""
        autocorr = np.correlate(waveform, waveform, mode='full')
        autocorr = autocorr[len(autocorr)//2:]
        peaks, _ = signal.find_peaks(
            autocorr[1:],
            height=np.max(autocorr[1:]) * 0.5
        )
        if len(peaks) > 0:
            return float(self.sample_rate / peaks[0])
        return 0.0
    
    def _compute_scale_invariance(self, waveform: np.ndarray) -> float:
        """Compute scale invariance metric."""
        scales = [1, 2, 4, 8]
        scale_energies = []
        for scale in scales:
            downsampled = waveform[::scale]
            energy = np.sum(downsampled ** 2)
            scale_energies.append(energy)
        
        if scale_energies[0] > 0:
            return float(np.std(scale_energies) / (np.mean(scale_energies) + 1e-10))
        return 0.0
    
    def print_analysis_report(self, results: Dict[str, float]):
        """
        Print a formatted analysis report to the console.
        
        Args:
            results: Dictionary of analysis results
        """
        print("\n" + "=" * 60)
        print("QUANTUM AUDIO SPECTRAL ANALYSIS REPORT")
        print("=" * 60)
        
        print("\n--- Basic Spectral Features ---")
        print(f"Spectral Centroid:      {results['spectral_centroid_hz']:.2f} Hz")
        print(f"Spectral Bandwidth:     {results['spectral_bandwidth_hz']:.2f} Hz")
        print(f"Spectral Rolloff:       {results['spectral_rolloff_hz']:.2f} Hz")
        print(f"Spectral Flatness:      {results['spectral_flatness']:.4f}")
        
        print("\n--- Non-Stationarity Analysis ---")
        print(f"Non-Stationarity Index: {results['non_stationarity_index']:.4f}")
        print(f"Temporal Variation:     {results['temporal_variation']:.4f}")
        
        print("\n--- Modulation Characteristics ---")
        print(f"Modulation Depth:              {results['modulation_depth']:.4f}")
        print(f"Frequency Modulation Index:    {results['frequency_modulation_index']:.4f}")
        print(f"Avg Spectral Spread:           {results['average_spectral_spread_hz']:.2f} Hz")
        print(f"Spectral Spread Variation:     {results['spectral_spread_variation']:.4f}")
        
        print("\n--- Quantum Pattern Indicators ---")
        print(f"Spectral Entropy:        {results['spectral_entropy']:.4f}")
        print(f"Mutual Information:     {results['mutual_information']:.4f} bits")
        print(f"Quantum Likelihood:     {results['quantum_likelihood_score']:.4f}")
        
        print("\n" + "=" * 60)
        print("Interpretation:")
        print("- High non-stationarity index suggests time-varying spectral content")
        print("- Higher mutual information suggests stronger bipartite correlations")
        print("- High spectral entropy suggests complex, non-classical structure")
        print("- Quantum likelihood score combines multiple indicators")
        print("=" * 60 + "\n")





