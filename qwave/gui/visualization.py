"""
Visualization Module

Reusable Matplotlib widgets for waveform and spectrogram plotting.
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from typing import Optional, Tuple


class WaveformPlotter:
    """Widget for plotting audio waveforms and spectra."""
    
    def __init__(self, parent, figsize=(6, 4), dpi=100):
        """
        Initialize waveform plotter.
        
        Args:
            parent: Parent widget
            figsize: Figure size tuple
            dpi: Dots per inch
        """
        self.figure = Figure(figsize=figsize, dpi=dpi)
        self.canvas = FigureCanvasTkAgg(self.figure, master=parent)
        
        # Create subplots
        self.ax_waveform = self.figure.add_subplot(211)
        self.ax_spectrum = self.figure.add_subplot(212)
        self.progress_line = None
        self.waveform_duration = 0.0
        
        self._setup_axes()
    
    def _setup_axes(self):
        """Setup initial axis labels and titles."""
        self.ax_waveform.set_title("Waveform")
        self.ax_waveform.set_xlabel("Time (s)")
        self.ax_waveform.set_ylabel("Amplitude")
        self.ax_spectrum.set_title("Magnitude Spectrum")
        self.ax_spectrum.set_xlabel("Frequency (Hz)")
        self.ax_spectrum.set_ylabel("Magnitude (dB)")
    
    def plot_waveform(self, waveform: np.ndarray, sample_rate: int):
        """
        Plot waveform and spectrum.
        
        Args:
            waveform: Audio waveform array
            sample_rate: Sample rate in Hz
        """
        # Convert to mono if stereo
        if waveform.ndim > 1:
            waveform = np.mean(waveform, axis=1)
        
        duration = len(waveform) / sample_rate
        self.waveform_duration = float(duration)
        time_axis = np.linspace(0, duration, len(waveform))
        
        # Downsample for display if too many points
        max_points = 5000
        if len(waveform) > max_points:
            indices = np.linspace(0, len(waveform) - 1, max_points).astype(int)
            waveform_display = waveform[indices]
            time_display = time_axis[indices]
        else:
            waveform_display = waveform
            time_display = time_axis
        
        # Clear and plot waveform
        self.ax_waveform.clear()
        self.ax_waveform.plot(time_display, waveform_display, linewidth=0.8)
        self.ax_waveform.set_title("Waveform")
        self.ax_waveform.set_xlabel("Time (s)")
        self.ax_waveform.set_ylabel("Amplitude")
        self.ax_waveform.margins(x=0)
        self.ax_waveform.grid(True, alpha=0.3)
        self.progress_line = self.ax_waveform.axvline(
            0.0, color="red", linewidth=1.0, label="Playback Position"
        )
        
        # Compute and plot spectrum
        freq_axis = np.fft.rfftfreq(len(waveform), d=1 / sample_rate)
        spectrum = np.abs(np.fft.rfft(waveform))
        spectrum_db = 20 * np.log10(spectrum + 1e-9)
        
        self.ax_spectrum.clear()
        self.ax_spectrum.plot(freq_axis, spectrum_db, color='#ff7043', linewidth=0.8)
        self.ax_spectrum.set_xlim(0, min(10000, freq_axis[-1]))
        self.ax_spectrum.set_ylim(np.max(spectrum_db) - 80, np.max(spectrum_db) + 5)
        self.ax_spectrum.set_xlabel("Frequency (Hz)")
        self.ax_spectrum.set_ylabel("Magnitude (dB)")
        self.ax_spectrum.grid(True, linestyle='--', linewidth=0.5, alpha=0.6)
        
        self.figure.tight_layout()
        self.canvas.draw()

    def set_playback_cursor(self, time_sec: float):
        """Update playback cursor on the waveform plot."""
        if self.progress_line is None:
            return
        x = max(0.0, min(float(time_sec), self.waveform_duration))
        self.progress_line.set_xdata([x, x])
        self.canvas.draw_idle()
    
    def clear(self):
        """Clear all plots."""
        self.ax_waveform.clear()
        self.ax_spectrum.clear()
        self.progress_line = None
        self.waveform_duration = 0.0
        self._setup_axes()
        self.canvas.draw()
    
    def get_widget(self):
        """Get the Tkinter widget."""
        return self.canvas.get_tk_widget()


class SpectrogramPlotter:
    """Widget for plotting spectrograms."""
    
    def __init__(self, parent, figsize=(8, 4), dpi=100):
        """
        Initialize spectrogram plotter.
        
        Args:
            parent: Parent widget
            figsize: Figure size tuple
            dpi: Dots per inch
        """
        self.figure = Figure(figsize=figsize, dpi=dpi)
        self.canvas = FigureCanvasTkAgg(self.figure, master=parent)
        self.ax = self.figure.add_subplot(111)
        self.im = None
    
    def plot_spectrogram(self, waveform: np.ndarray, sample_rate: int, 
                        n_fft: int = 2048, hop_length: int = 512):
        """
        Plot spectrogram.
        
        Args:
            waveform: Audio waveform array
            sample_rate: Sample rate in Hz
            n_fft: FFT window size
            hop_length: Hop length
        """
        import librosa
        
        # Convert to mono if stereo
        if waveform.ndim > 1:
            waveform = np.mean(waveform, axis=1)
        
        # Compute spectrogram
        stft = librosa.stft(waveform, n_fft=n_fft, hop_length=hop_length)
        magnitude = np.abs(stft) ** 2
        spectrogram_db = librosa.power_to_db(magnitude, ref=np.max)
        
        # Time and frequency axes
        times = librosa.frames_to_time(
            np.arange(spectrogram_db.shape[1]),
            sr=sample_rate,
            hop_length=hop_length
        )
        frequencies = librosa.fft_frequencies(sr=sample_rate, n_fft=n_fft)
        
        # Clear and plot
        self.ax.clear()
        self.im = self.ax.pcolormesh(times, frequencies, spectrogram_db, 
                                     cmap='magma', shading='gouraud')
        self.ax.set_title("Spectrogram")
        self.ax.set_xlabel("Time (s)")
        self.ax.set_ylabel("Frequency (Hz)")
        self.ax.set_ylim([0, 5000])
        self.figure.colorbar(self.im, ax=self.ax, label='Power (dB)')
        
        self.figure.tight_layout()
        self.canvas.draw()
    
    def clear(self):
        """Clear the plot."""
        self.ax.clear()
        self.im = None
        self.canvas.draw()
    
    def get_widget(self):
        """Get the Tkinter widget."""
        return self.canvas.get_tk_widget()


class FeatureVisualizer:
    """Widget for visualizing audio features."""
    
    def __init__(self, parent, figsize=(6, 4), dpi=100):
        """
        Initialize feature visualizer.
        
        Args:
            parent: Parent widget
            figsize: Figure size tuple
            dpi: Dots per inch
        """
        self.figure = Figure(figsize=figsize, dpi=dpi)
        self.canvas = FigureCanvasTkAgg(self.figure, master=parent)
        self.ax = self.figure.add_subplot(111)
    
    def plot_features(self, features: dict, max_features: int = 10):
        """
        Plot audio features as a bar chart.
        
        Args:
            features: Dictionary of feature names and values
            max_features: Maximum number of features to display
        """
        # Select features to display
        feature_items = list(features.items())[:max_features]
        feature_names = [name.replace('_', ' ').title() for name, _ in feature_items]
        feature_values = [value for _, value in feature_items]
        
        # Clear and plot
        self.ax.clear()
        self.ax.bar(range(len(feature_names)), feature_values, alpha=0.7)
        self.ax.set_title("Audio Features")
        self.ax.set_ylabel("Value")
        self.ax.set_xticks(range(len(feature_names)))
        self.ax.set_xticklabels(feature_names, rotation=45, ha='right')
        self.ax.grid(True, alpha=0.3, axis='y')
        
        self.figure.tight_layout()
        self.canvas.draw()
    
    def clear(self):
        """Clear the plot."""
        self.ax.clear()
        self.canvas.draw()
    
    def get_widget(self):
        """Get the Tkinter widget."""
        return self.canvas.get_tk_widget()


class MultiPanelVisualizer:
    """Widget for displaying multiple visualizations in a grid."""
    
    def __init__(self, parent, nrows: int = 2, ncols: int = 2, 
                 figsize=(10, 8), dpi=100):
        """
        Initialize multi-panel visualizer.
        
        Args:
            parent: Parent widget
            nrows: Number of rows
            ncols: Number of columns
            figsize: Figure size tuple
            dpi: Dots per inch
        """
        self.figure = Figure(figsize=figsize, dpi=dpi)
        self.canvas = FigureCanvasTkAgg(self.figure, master=parent)
        self.axes = self.figure.subplots(nrows, ncols)
        
        # Flatten axes if 2D
        if nrows > 1 and ncols > 1:
            self.axes = self.axes.flatten()
        elif nrows == 1 or ncols == 1:
            self.axes = [self.axes] if not isinstance(self.axes, list) else self.axes
    
    def plot_waveform(self, waveform: np.ndarray, sample_rate: int, ax_idx: int = 0):
        """Plot waveform in specified axis."""
        ax = self.axes[ax_idx]
        duration = len(waveform) / sample_rate
        time_axis = np.linspace(0, duration, len(waveform))
        
        if waveform.ndim > 1:
            waveform = np.mean(waveform, axis=1)
        
        ax.clear()
        ax.plot(time_axis, waveform, linewidth=0.8)
        ax.set_title("Waveform")
        ax.set_xlabel("Time (s)")
        ax.set_ylabel("Amplitude")
        ax.grid(True, alpha=0.3)
        self.canvas.draw()
    
    def plot_spectrum(self, waveform: np.ndarray, sample_rate: int, ax_idx: int = 1):
        """Plot frequency spectrum in specified axis."""
        ax = self.axes[ax_idx]
        
        if waveform.ndim > 1:
            waveform = np.mean(waveform, axis=1)
        
        freq_axis = np.fft.rfftfreq(len(waveform), d=1 / sample_rate)
        spectrum = np.abs(np.fft.rfft(waveform))
        spectrum_db = 20 * np.log10(spectrum + 1e-9)
        
        ax.clear()
        ax.semilogy(freq_axis[:5000], spectrum_db[:5000])
        ax.set_title("Frequency Spectrum")
        ax.set_xlabel("Frequency (Hz)")
        ax.set_ylabel("Magnitude")
        ax.grid(True, alpha=0.3)
        self.canvas.draw()
    
    def plot_spectrogram(self, waveform: np.ndarray, sample_rate: int, ax_idx: int = 2):
        """Plot spectrogram in specified axis."""
        import librosa
        ax = self.axes[ax_idx]
        
        if waveform.ndim > 1:
            waveform = np.mean(waveform, axis=1)
        
        spectrogram, times, frequencies = self._compute_spectrogram(waveform, sample_rate)
        
        ax.clear()
        im = ax.pcolormesh(times, frequencies, spectrogram, cmap='viridis', shading='gouraud')
        ax.set_title("Spectrogram")
        ax.set_xlabel("Time (s)")
        ax.set_ylabel("Frequency (Hz)")
        ax.set_ylim([0, 5000])
        self.figure.colorbar(im, ax=ax)
        self.canvas.draw()
    
    def plot_features(self, features: dict, ax_idx: int = 3, max_features: int = 5):
        """Plot features in specified axis."""
        ax = self.axes[ax_idx]
        
        feature_items = list(features.items())[:max_features]
        feature_names = [name.replace('_', ' ').title() for name, _ in feature_items]
        feature_values = [value for _, value in feature_items]
        
        ax.clear()
        ax.bar(range(len(feature_names)), feature_values)
        ax.set_title("Audio Features")
        ax.set_ylabel("Value")
        ax.set_xticks(range(len(feature_names)))
        ax.set_xticklabels(feature_names, rotation=45, ha='right')
        ax.grid(True, alpha=0.3, axis='y')
        self.canvas.draw()
    
    def _compute_spectrogram(self, waveform: np.ndarray, sample_rate: int):
        """Compute spectrogram using librosa."""
        import librosa
        stft = librosa.stft(waveform, n_fft=2048, hop_length=512)
        magnitude = np.abs(stft) ** 2
        spectrogram_db = librosa.power_to_db(magnitude, ref=np.max)
        
        times = librosa.frames_to_time(
            np.arange(spectrogram_db.shape[1]),
            sr=sample_rate,
            hop_length=512
        )
        frequencies = librosa.fft_frequencies(sr=sample_rate, n_fft=2048)
        
        return spectrogram_db, times, frequencies
    
    def clear(self):
        """Clear all plots."""
        for ax in self.axes:
            ax.clear()
            ax.set_xticks([])
            ax.set_yticks([])
        self.canvas.draw()
    
    def get_widget(self):
        """Get the Tkinter widget."""
        return self.canvas.get_tk_widget()





