"""
Spectral Analysis Module

This module performs spectral analysis on generated audio to detect and quantify
non-classical audio patterns, such as non-stationarity and quantum interference effects.
"""

import numpy as np
import librosa
from typing import Dict, Tuple
from scipy import signal
from scipy.stats import entropy


class SpectralAnalyzer:
    """
    Analyzes audio waveforms to detect non-classical patterns.
    
    This class implements various spectral analysis techniques to identify
    characteristics that distinguish quantum-generated audio from classical
    noise or random audio patterns.
    """
    
    def __init__(self, sample_rate: int = 44100):
        """
        Initialize the spectral analyzer.
        
        Args:
            sample_rate: Audio sample rate in Hz (default: 44100)
        """
        self.sample_rate = sample_rate
    
    def analyze(self, waveform: np.ndarray) -> Dict[str, float]:
        """
        Perform comprehensive spectral analysis on the audio waveform.
        
        Args:
            waveform: Audio waveform array
            
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
        results.update(self._compute_quantum_indicators(waveform))
        
        return results
    
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
        spectral_centroid = np.sum(frequencies * psd) / np.sum(psd)
        
        # Spectral bandwidth
        spectral_bandwidth = np.sqrt(
            np.sum(((frequencies - spectral_centroid) ** 2) * psd) / np.sum(psd)
        )
        
        # Spectral rolloff (frequency below which 85% of energy is contained)
        cumsum_psd = np.cumsum(psd)
        rolloff_index = np.where(cumsum_psd >= 0.85 * cumsum_psd[-1])[0]
        spectral_rolloff = frequencies[rolloff_index[0]] if len(rolloff_index) > 0 else frequencies[-1]
        
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
    
    def _compute_quantum_indicators(self, waveform: np.ndarray) -> Dict[str, float]:
        """
        Compute indicators specific to quantum-generated audio.
        
        These metrics attempt to capture characteristics that might indicate
        quantum interference patterns.
        
        Args:
            waveform: Audio waveform array
            
        Returns:
            Dictionary of quantum-specific metrics
        """
        # Compute power spectral density
        frequencies, psd = signal.welch(
            waveform,
            self.sample_rate,
            nperseg=min(2048, len(waveform) // 4)
        )
        
        # Normalize PSD
        psd_normalized = psd / (np.sum(psd) + 1e-10)
        
        # Spectral entropy (measure of spectral complexity)
        # Higher entropy suggests more complex, potentially quantum-like patterns
        spectral_entropy = entropy(psd_normalized + 1e-10)
        
        # Interference pattern strength
        # Look for patterns in phase relationships
        analytic_signal = signal.hilbert(waveform)
        phase = np.angle(analytic_signal)
        phase_diff = np.diff(phase)
        
        # Measure phase coherence (quantum interference should show specific phase patterns)
        phase_coherence = np.abs(np.mean(np.exp(1j * phase_diff)))
        
        # Spectral periodicity breakdown
        # Quantum interference might break classical periodicity
        autocorr = np.correlate(waveform, waveform, mode='full')
        autocorr = autocorr[len(autocorr) // 2:]
        autocorr = autocorr / (autocorr[0] + 1e-10)
        
        # Find dominant period
        # Look for peaks in autocorrelation (excluding zero lag)
        if len(autocorr) > 100:
            peaks, _ = signal.find_peaks(autocorr[1:1000], height=0.1)
            if len(peaks) > 0:
                periodicity_strength = np.max(autocorr[peaks])
            else:
                periodicity_strength = 0.0
        else:
            periodicity_strength = 0.0
        
        return {
            'spectral_entropy': spectral_entropy,
            'phase_coherence': phase_coherence,
            'periodicity_strength': periodicity_strength,
            'quantum_likelihood_score': (spectral_entropy * (1 - phase_coherence) * (1 - periodicity_strength))
        }
    
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
        print(f"Phase Coherence:        {results['phase_coherence']:.4f}")
        print(f"Periodicity Strength:   {results['periodicity_strength']:.4f}")
        print(f"Quantum Likelihood:     {results['quantum_likelihood_score']:.4f}")
        
        print("\n" + "=" * 60)
        print("Interpretation:")
        print("- High non-stationarity index suggests time-varying spectral content")
        print("- Low phase coherence may indicate quantum interference patterns")
        print("- High spectral entropy suggests complex, non-classical structure")
        print("- Quantum likelihood score combines multiple indicators")
        print("=" * 60 + "\n")

