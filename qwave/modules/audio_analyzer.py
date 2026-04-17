"""
Module C-1: Audio Analysis Functions
Spectrogram analysis and audio feature extraction
"""

import numpy as np
import matplotlib.pyplot as plt
import librosa
import soundfile as sf
from typing import Dict, Tuple, Optional
from scipy import signal
from scipy.fft import fft, fftfreq

from qwave.utils.constants import SAMPLING_RATE


class AudioAnalyzer:
    """Class for analyzing and visualizing audio waveforms"""
    
    def __init__(self, sampling_rate: int = SAMPLING_RATE):
        """
        Args:
            sampling_rate: Sampling frequency
        """
        self.sampling_rate = sampling_rate
    
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
            sr=self.sampling_rate,
            hop_length=hop_length
        )
        
        # Frequency axis
        frequencies = librosa.fft_frequencies(sr=self.sampling_rate, n_fft=n_fft)
        
        return spectrogram_db, times, frequencies
    
    def plot_spectrogram(
        self,
        waveform: np.ndarray,
        output_file: Optional[str] = None,
        title: str = "Spectrogram"
    ) -> None:
        """
        Visualize spectrogram
        
        Args:
            waveform: Waveform data
            output_file: Output file path
            title: Title
        """
        # Compute spectrogram
        spectrogram, times, frequencies = self.compute_spectrogram(waveform)
        
        # Plot
        plt.figure(figsize=(12, 6))
        
        plt.subplot(2, 1, 1)
        plt.plot(np.linspace(0, len(waveform) / self.sampling_rate, len(waveform)), waveform)
        plt.xlabel('Time (s)')
        plt.ylabel('Amplitude')
        plt.title('Waveform')
        plt.grid(True, alpha=0.3)
        
        plt.subplot(2, 1, 2)
        plt.pcolormesh(times, frequencies, spectrogram, cmap='viridis', shading='gouraud')
        plt.xlabel('Time (s)')
        plt.ylabel('Frequency (Hz)')
        plt.title(title)
        plt.colorbar(label='Power (dB)')
        plt.ylim([0, 5000])  # Display up to 5kHz
        
        plt.tight_layout()
        
        if output_file:
            plt.savefig(output_file, dpi=150)
            print(f"Spectrogram saved to: {output_file}")
        else:
            plt.show()
    
    def analyze_audio_features(self, waveform: np.ndarray) -> Dict[str, float]:
        """
        Analyze audio features
        
        Args:
            waveform: Waveform data
            
        Returns:
            Feature dictionary
        """
        features = {}
        
        # FFT
        fft_data = np.abs(fft(waveform))
        freqs = fftfreq(len(waveform), 1/self.sampling_rate)
        positive_freqs = freqs[:len(freqs)//2]
        positive_fft = fft_data[:len(fft_data)//2]
        
        # 1. Spectral entropy
        if np.sum(positive_fft) > 0:
            normalized_fft = positive_fft / np.sum(positive_fft)
            spectral_entropy = -np.sum(
                normalized_fft * np.log(normalized_fft + 1e-10)
            )
            features['spectral_entropy'] = spectral_entropy
        else:
            features['spectral_entropy'] = 0.0
        
        # 2. Spectral centroid
        if np.sum(positive_fft) > 0:
            spectral_centroid = np.sum(positive_freqs * positive_fft) / np.sum(positive_fft)
            features['spectral_centroid'] = spectral_centroid
        else:
            features['spectral_centroid'] = 0.0
        
        # 3. Spectral rolloff
        cumsum_fft = np.cumsum(positive_fft)
        total_energy = cumsum_fft[-1]
        if total_energy > 0:
            rolloff_idx = np.where(cumsum_fft >= 0.85 * total_energy)[0]
            if len(rolloff_idx) > 0:
                features['spectral_rolloff'] = positive_freqs[rolloff_idx[0]]
            else:
                features['spectral_rolloff'] = positive_freqs[-1]
        else:
            features['spectral_rolloff'] = 0.0
        
        # 4. Zero crossing rate
        zcr = np.mean(librosa.feature.zero_crossing_rate(waveform))
        features['zero_crossing_rate'] = float(zcr)
        
        # 5. Autocorrelation (periodicity detection)
        autocorr = np.correlate(waveform, waveform, mode='full')
        autocorr = autocorr[len(autocorr)//2:]
        # Detect first peak (fundamental frequency)
        peaks, _ = signal.find_peaks(
            autocorr[1:],
            height=np.max(autocorr[1:]) * 0.5
        )
        if len(peaks) > 0:
            fundamental_freq = self.sampling_rate / peaks[0]
            features['fundamental_frequency'] = fundamental_freq
        else:
            features['fundamental_frequency'] = 0.0
        
        # 6. Temporal modulation characteristics (quantum non-stationarity indicator)
        # Spectral centroid variation in short time windows
        window_size = self.sampling_rate // 10  # 100ms window
        n_windows = len(waveform) // window_size
        
        if n_windows > 1:
            spectral_centroids = []
            for i in range(n_windows):
                start = i * window_size
                end = start + window_size
                window_fft = np.abs(fft(waveform[start:end]))
                window_freqs = fftfreq(window_size, 1/self.sampling_rate)
                pos_window_freqs = window_freqs[:len(window_freqs)//2]
                pos_window_fft = window_fft[:len(window_fft)//2]
                
                if np.sum(pos_window_fft) > 0:
                    centroid = np.sum(pos_window_freqs * pos_window_fft) / np.sum(pos_window_fft)
                    spectral_centroids.append(centroid)
            
            if spectral_centroids:
                features['temporal_modulation'] = np.std(spectral_centroids)
            else:
                features['temporal_modulation'] = 0.0
        else:
            features['temporal_modulation'] = 0.0
        
        # 7. Scale invariance (quantum interference pattern indicator)
        # Energy ratio across multiple scales
        scales = [1, 2, 4, 8]
        scale_energies = []
        for scale in scales:
            downsampled = waveform[::scale]
            energy = np.sum(downsampled ** 2)
            scale_energies.append(energy)
        
        if scale_energies[0] > 0:
            scale_invariance = np.std(scale_energies) / (np.mean(scale_energies) + 1e-10)
            features['scale_invariance'] = scale_invariance
        else:
            features['scale_invariance'] = 0.0
        
        return features
    
    def compare_with_classical(self, quantum_wave: np.ndarray, classical_wave: np.ndarray) -> Dict[str, float]:
        """
        Compare quantum-generated waveform with classical waveform
        
        Args:
            quantum_wave: Quantum-generated waveform
            classical_wave: Classical waveform
            
        Returns:
            Comparison metrics
        """
        # Extract features
        quantum_features = self.analyze_audio_features(quantum_wave)
        classical_features = self.analyze_audio_features(classical_wave)
        
        # Calculate feature differences
        comparison = {}
        for key in quantum_features.keys():
            comparison[f'{key}_quantum'] = quantum_features[key]
            comparison[f'{key}_classical'] = classical_features[key]
            comparison[f'{key}_difference'] = abs(
                quantum_features[key] - classical_features[key]
            )
        
        # Spectral distance
        q_fft = np.abs(fft(quantum_wave))[:len(quantum_wave)//2]
        c_fft = np.abs(fft(classical_wave))[:len(classical_wave)//2]
        
        # Align lengths
        min_len = min(len(q_fft), len(c_fft))
        q_fft = q_fft[:min_len]
        c_fft = c_fft[:min_len]
        
        # Normalize
        if np.sum(q_fft) > 0:
            q_fft = q_fft / np.sum(q_fft)
        if np.sum(c_fft) > 0:
            c_fft = c_fft / np.sum(c_fft)
        
        # Spectral distance
        spectral_distance = np.sum((q_fft - c_fft) ** 2)
        comparison['spectral_distance'] = spectral_distance
        
        return comparison
    
    def generate_classical_comparison(self, duration: float = 2.0) -> np.ndarray:
        """
        Generate classical noise waveform for comparison
        
        Args:
            duration: Waveform length (seconds)
            
        Returns:
            Classical noise waveform
        """
        n_samples = int(duration * self.sampling_rate)
        
        # Gaussian white noise
        noise = np.random.normal(0, 0.5, n_samples)
        
        # Filtering (to make it more musical)
        from scipy.signal import butter, lfilter
        b, a = butter(4, 0.3, btype='low')
        filtered = lfilter(b, a, noise)
        
        # Normalize
        if np.max(np.abs(filtered)) > 0:
            filtered = filtered / np.max(np.abs(filtered))
        
        return filtered
    
    def visualize_quantum_vs_classical(
        self,
        quantum_wave: np.ndarray,
        classical_wave: Optional[np.ndarray] = None,
        output_file: Optional[str] = None
    ) -> None:
        """
        Visualize comparison between quantum and classical waveforms
        
        Args:
            quantum_wave: Quantum waveform
            classical_wave: Classical waveform (auto-generated if None)
            output_file: Output file path
        """
        if classical_wave is None:
            classical_wave = self.generate_classical_comparison(
                duration=len(quantum_wave) / self.sampling_rate
            )
        
        # Calculate features
        q_features = self.analyze_audio_features(quantum_wave)
        c_features = self.analyze_audio_features(classical_wave)
        
        # Visualization
        fig, axes = plt.subplots(2, 3, figsize=(18, 10))
        
        # Waveform comparison
        time_axis = np.linspace(0, len(quantum_wave) / self.sampling_rate, len(quantum_wave))
        axes[0, 0].plot(time_axis, quantum_wave, label='Quantum', alpha=0.7)
        axes[0, 0].plot(time_axis, classical_wave, label='Classical', alpha=0.7)
        axes[0, 0].set_xlabel('Time (s)')
        axes[0, 0].set_ylabel('Amplitude')
        axes[0, 0].set_title('Waveform Comparison')
        axes[0, 0].legend()
        axes[0, 0].grid(True, alpha=0.3)
        
        # Spectrum comparison
        q_fft = np.abs(fft(quantum_wave))[:len(quantum_wave)//2]
        c_fft = np.abs(fft(classical_wave))[:len(classical_wave)//2]
        freqs = np.fft.fftfreq(len(quantum_wave), 1/self.sampling_rate)[:len(quantum_wave)//2]
        
        min_len = min(len(q_fft), len(c_fft))
        axes[0, 1].semilogy(freqs[:min_len], q_fft[:min_len], label='Quantum', alpha=0.7)
        axes[0, 1].semilogy(freqs[:min_len], c_fft[:min_len], label='Classical', alpha=0.7)
        axes[0, 1].set_xlabel('Frequency (Hz)')
        axes[0, 1].set_ylabel('Magnitude')
        axes[0, 1].set_title('Frequency Spectrum')
        axes[0, 1].legend()
        axes[0, 1].grid(True, alpha=0.3)
        axes[0, 1].set_xlim([0, 5000])
        
        # Spectrogram (quantum)
        spec_q, times_q, freq_q = self.compute_spectrogram(quantum_wave)
        im1 = axes[0, 2].pcolormesh(times_q, freq_q, spec_q, cmap='viridis', shading='gouraud')
        axes[0, 2].set_xlabel('Time (s)')
        axes[0, 2].set_ylabel('Frequency (Hz)')
        axes[0, 2].set_title('Quantum Spectrogram')
        axes[0, 2].set_ylim([0, 5000])
        plt.colorbar(im1, ax=axes[0, 2])
        
        # Spectrogram (classical)
        spec_c, times_c, freq_c = self.compute_spectrogram(classical_wave)
        im2 = axes[1, 0].pcolormesh(times_c, freq_c, spec_c, cmap='viridis', shading='gouraud')
        axes[1, 0].set_xlabel('Time (s)')
        axes[1, 0].set_ylabel('Frequency (Hz)')
        axes[1, 0].set_title('Classical Spectrogram')
        axes[1, 0].set_ylim([0, 5000])
        plt.colorbar(im2, ax=axes[1, 0])
        
        # Feature comparison
        features_to_plot = ['spectral_entropy', 'spectral_centroid', 'temporal_modulation']
        q_vals = [q_features.get(f, 0) for f in features_to_plot]
        c_vals = [c_features.get(f, 0) for f in features_to_plot]
        
        x = np.arange(len(features_to_plot))
        width = 0.35
        axes[1, 1].bar(x - width/2, q_vals, width, label='Quantum', alpha=0.7)
        axes[1, 1].bar(x + width/2, c_vals, width, label='Classical', alpha=0.7)
        axes[1, 1].set_xlabel('Features')
        axes[1, 1].set_ylabel('Value')
        axes[1, 1].set_title('Feature Comparison')
        axes[1, 1].set_xticks(x)
        axes[1, 1].set_xticklabels(features_to_plot, rotation=45, ha='right')
        axes[1, 1].legend()
        axes[1, 1].grid(True, alpha=0.3)
        
        # Feature table
        axes[1, 2].axis('off')
        table_data = []
        for f in features_to_plot:
            table_data.append([
                f,
                f"{q_features.get(f, 0):.3f}",
                f"{c_features.get(f, 0):.3f}"
            ])
        
        table = axes[1, 2].table(
            cellText=table_data,
            colLabels=['Feature', 'Quantum', 'Classical'],
            cellLoc='center',
            loc='center'
        )
        table.auto_set_font_size(False)
        table.set_fontsize(10)
        table.scale(1.2, 1.5)
        axes[1, 2].set_title('Feature Values')
        
        plt.tight_layout()
        
        if output_file:
            plt.savefig(output_file, dpi=150)
            print(f"Comparison plot saved to: {output_file}")
        else:
            plt.show()
