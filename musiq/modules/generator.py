"""
Audio Generation Module

This module maps quantum measurement results and statevectors to audio waveforms,
creating non-classical audio patterns based on quantum interference.
"""

import numpy as np
from typing import List, Optional, Dict
import soundfile as sf
from scipy.signal import butter, filtfilt
from pathlib import Path

from qwave.utils.constants import SAMPLING_RATE, DEFAULT_DURATION, DEFAULT_ROOM_SIZE


class AudioGenerator:
    """
    Generates audio waveforms from quantum measurement results.
    
    This class implements algorithms to convert quantum interference patterns
    into time-domain audio signals, creating non-classical sound patterns that
    reflect the quantum nature of the source circuit.
    """
    
    NOTE_FREQUENCIES = np.array([
        110.00, 123.47, 130.81, 146.83, 164.81, 174.61, 196.00,
        220.00, 246.94, 261.63, 293.66, 329.63, 349.23, 392.00,
        440.00, 493.88, 523.25, 587.33, 659.25, 698.46, 783.99,
        880.00
    ])

    def __init__(self, sample_rate: int = SAMPLING_RATE):
        """
        Initialize the audio generator.
        
        Args:
            sample_rate: Audio sample rate in Hz (default: 44100)
        """
        self.sample_rate = sample_rate
        self.max_octave_spread = 3
    
    def map_quantum_to_audio(
        self,
        statevector: Optional[np.ndarray] = None,
        measurement_sequence: Optional[List[int]] = None,
        probability_distribution: Optional[np.ndarray] = None,
        duration: float = DEFAULT_DURATION,
        apply_envelope: bool = True,
        apply_reverb: bool = False,
        interference_mode: bool = False,
    ) -> np.ndarray:
        """
        Map quantum measurement results to audio waveform.
        
        This is the core algorithm that transforms quantum interference patterns
        into audio signals. It uses both amplitude and phase information from
        the quantum state to create non-classical audio patterns.
        
        Args:
            statevector: Quantum statevector (complex amplitudes)
            measurement_sequence: Sequence of measurement outcomes
            probability_distribution: Probability distribution over states
            duration: Duration of audio in seconds
            apply_envelope: Apply ADSR envelope (default: True)
            apply_reverb: Apply reverb effect (default: False)
            interference_mode: If True, use phase-driven constructive/destructive
                interference between adjacent states (sonification of quantum interference).
            
        Returns:
            Audio waveform as numpy array (normalized to [-1, 1])
        """
        num_samples = int(self.sample_rate * duration)
        waveform = np.zeros(num_samples)
        
        # Primary method: Use statevector for interference patterns
        if statevector is not None:
            waveform = self._generate_from_statevector(
                statevector, num_samples, interference_mode=interference_mode
            )
        # Fallback: Use measurement sequence
        elif measurement_sequence is not None:
            waveform = self._generate_from_sequence(measurement_sequence, num_samples)
        # Last resort: Use probability distribution
        elif probability_distribution is not None:
            waveform = self._generate_from_probabilities(probability_distribution, num_samples)
        else:
            raise ValueError("At least one of statevector, measurement_sequence, or probability_distribution must be provided")
        
        # Apply audio effects
        if apply_envelope:
            waveform = self._apply_envelope(waveform, duration)
        
        if apply_reverb:
            waveform = self._add_reverb(waveform, room_size=DEFAULT_ROOM_SIZE)
        
        # Normalize to prevent clipping
        max_amplitude = np.max(np.abs(waveform))
        if max_amplitude > 0:
            waveform = waveform / max_amplitude * 0.95  # Leave headroom
        
        return waveform
    
    def _generate_from_statevector(
        self,
        statevector: np.ndarray,
        num_samples: int,
        interference_mode: bool = False,
    ) -> np.ndarray:
        """
        Generate audio from quantum statevector using interference patterns.
        
        This method captures quantum interference by using the phase and amplitude
        information from the statevector to modulate frequency and amplitude.
        When interference_mode is True, phase alignment between adjacent active
        states boosts (constructive) or dampens (destructive) contributions.
        
        Args:
            statevector: Complex quantum statevector
            num_samples: Number of audio samples to generate
            interference_mode: If True, apply phase-driven constructive/destructive weighting.
            
        Returns:
            Audio waveform array
        """
        waveform = np.zeros(num_samples, dtype=np.float32)
        amplitudes = np.abs(statevector)
        phases = np.angle(statevector)
        if np.max(amplitudes) > 0:
            amplitudes = amplitudes / np.max(amplitudes)

        t = np.linspace(0, num_samples / self.sample_rate, num_samples)
        envelope = np.sin(np.pi * t / t[-1]) ** 2

        for idx, (amp, phase) in enumerate(zip(amplitudes, phases)):
            if amp < 1e-3:
                continue
            # Phase-driven interference: weight by alignment with previous active state
            if interference_mode and idx > 0:
                phase_diff = phase - phases[idx - 1]
                # cos(0)=1 (constructive) -> factor 1; cos(pi)=-1 (destructive) -> factor 0
                interference_factor = 0.5 + 0.5 * np.cos(phase_diff)
            else:
                interference_factor = 1.0

            freq = self._index_to_musical_frequency(idx)
            harmonic_mix = (
                0.7 * np.sin(2 * np.pi * freq * t + phase) +
                0.2 * np.sin(2 * np.pi * freq * 2 * t + phase * 1.5) +
                0.1 * np.sin(2 * np.pi * freq * 3 * t + phase * 2.0)
            )
            vib = 1 + 0.015 * np.sin(2 * np.pi * 5 * t + phase)
            waveform += (amp * interference_factor) * harmonic_mix * vib

        waveform *= envelope
        waveform = self._apply_lowpass_filter(waveform, cutoff=6000.0)
        waveform = self._normalize_waveform(waveform)
        return waveform.astype(np.float32)
    
    def _generate_from_sequence(
        self,
        measurement_sequence: List[int],
        num_samples: int
    ) -> np.ndarray:
        """
        Generate audio from measurement sequence.
        
        Args:
            measurement_sequence: List of measurement outcomes
            num_samples: Number of audio samples to generate
            
        Returns:
            Audio waveform array
        """
        if len(measurement_sequence) == 0:
            return np.zeros(num_samples)
        
        # Map measurement outcomes to audio samples
        sequence_array = np.array(measurement_sequence)
        
        # Interpolate sequence to match desired number of samples
        if len(sequence_array) < num_samples:
            # Upsample using interpolation
            indices = np.linspace(0, len(sequence_array) - 1, num_samples)
            waveform = np.interp(indices, np.arange(len(sequence_array)), sequence_array)
        else:
            # Downsample
            indices = np.linspace(0, len(sequence_array) - 1, num_samples).astype(int)
            waveform = sequence_array[indices]
        
        # Normalize and convert to audio range
        max_val = np.max(np.abs(waveform))
        if max_val > 0:
            waveform = (waveform - np.mean(waveform)) / max_val
        
        t = np.linspace(0, num_samples / self.sample_rate, num_samples)
        freq_stream = np.array([self._index_to_musical_frequency(int(v)) for v in waveform])
        freq_mod = np.interp(t, np.linspace(0, t[-1], len(freq_stream)), freq_stream)
        waveform = np.sin(2 * np.pi * freq_mod * t)
        waveform = self._apply_lowpass_filter(waveform, cutoff=5000.0)
        waveform = self._normalize_waveform(waveform)
        return waveform.astype(np.float32)
    
    def _generate_from_probabilities(
        self,
        probability_distribution: np.ndarray,
        num_samples: int
    ) -> np.ndarray:
        """
        Generate audio from probability distribution.
        
        Args:
            probability_distribution: Probability array
            num_samples: Number of audio samples to generate
            
        Returns:
            Audio waveform array
        """
        num_states = len(probability_distribution)
        waveform = np.zeros(num_samples, dtype=np.float32)
        
        # Create frequency components weighted by probabilities
        base_freq = 20.0
        freq_range = 20000.0 - base_freq
        
        t = np.linspace(0, num_samples / self.sample_rate, num_samples)
        
        for i, prob in enumerate(probability_distribution):
            freq = base_freq + (freq_range * np.log1p(i) / np.log1p(num_states))
            component = prob * np.sin(2 * np.pi * freq * t)
            waveform += component
        
        waveform = self._apply_lowpass_filter(waveform, cutoff=6000.0)
        waveform = self._normalize_waveform(waveform)
        return waveform
    
    def _apply_envelope(self, waveform: np.ndarray, duration: float) -> np.ndarray:
        """
        Apply ADSR envelope to create natural sound.
        
        Args:
            waveform: Original waveform
            duration: Duration in seconds
            
        Returns:
            Waveform with envelope applied
        """
        n_samples = len(waveform)
        
        # ADSR parameters
        attack_time = 0.05   # Attack time (seconds)
        decay_time = 0.1     # Decay time (seconds)
        sustain_level = 0.7  # Sustain level
        release_time = 0.3   # Release time (seconds)
        
        # Convert to sample count
        attack_samples = int(attack_time * self.sample_rate)
        decay_samples = int(decay_time * self.sample_rate)
        release_samples = int(release_time * self.sample_rate)
        
        envelope = np.ones(n_samples)
        
        # Attack
        if attack_samples > 0:
            envelope[:attack_samples] = np.linspace(0, 1, attack_samples)
        
        # Decay
        if decay_samples > 0:
            end_idx = min(attack_samples + decay_samples, n_samples)
            decay_curve = np.linspace(1, sustain_level, decay_samples)
            envelope[attack_samples:end_idx] = decay_curve[:end_idx-attack_samples]
        
        # Sustain (flat)
        sustain_start = attack_samples + decay_samples
        sustain_end = n_samples - release_samples
        if sustain_end > sustain_start:
            envelope[sustain_start:sustain_end] = sustain_level
        
        # Release
        if release_samples > 0:
            envelope[-release_samples:] = np.linspace(
                sustain_level, 0, release_samples
            )
        
        return waveform * envelope
    
    def _add_reverb(self, waveform: np.ndarray, room_size: float = DEFAULT_ROOM_SIZE) -> np.ndarray:
        """
        Add simple reverb effect.
        
        Args:
            waveform: Original waveform
            room_size: Reverb size (0.0-1.0)
            
        Returns:
            Waveform with reverb applied
        """
        delay_samples = int(0.03 * self.sample_rate * room_size)  # 30ms delay
        reverb_wave = np.zeros(len(waveform) + delay_samples)
        
        reverb_wave[:len(waveform)] = waveform
        reverb_wave[delay_samples:] += waveform * 0.3 * room_size
        
        return reverb_wave[:len(waveform)]
    
    def _index_to_musical_frequency(self, index: int) -> float:
        """Convert state index to musical frequency."""
        palette_len = len(self.NOTE_FREQUENCIES)
        note = self.NOTE_FREQUENCIES[index % palette_len]
        octave = min(index // palette_len, self.max_octave_spread)
        return note * (2 ** max(octave - 1, 0))

    def _apply_lowpass_filter(self, waveform: np.ndarray, cutoff: float) -> np.ndarray:
        """Apply lowpass filter to waveform."""
        if cutoff >= (self.sample_rate / 2) or len(waveform) < 8:
            return waveform
        normalized_cutoff = cutoff / (self.sample_rate / 2)
        b, a = butter(4, normalized_cutoff, btype='low')
        return filtfilt(b, a, waveform).astype(np.float32)

    def _normalize_waveform(self, waveform: np.ndarray) -> np.ndarray:
        """Normalize waveform to prevent clipping."""
        peak = np.max(np.abs(waveform))
        if peak > 0:
            waveform = waveform / peak * 0.9
        return waveform
    
    def save_wav(self, waveform: np.ndarray, output_path: str, subtype: str = 'PCM_16'):
        """
        Save audio waveform to WAV file.
        
        Args:
            waveform: Audio waveform array (normalized to [-1, 1])
            output_path: Path to output WAV file
            subtype: WAV subtype (default: PCM_16 for compatibility)
        """
        # Ensure waveform is in correct format
        if waveform.dtype != np.float32:
            waveform = waveform.astype(np.float32)
        
        # Ensure values are in valid range
        waveform = np.clip(waveform, -1.0, 1.0)
        
        # Create output directory if needed
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Save to file
        sf.write(output_path, waveform, self.sample_rate, subtype=subtype)
        print(f"Audio saved to: {output_path}")





