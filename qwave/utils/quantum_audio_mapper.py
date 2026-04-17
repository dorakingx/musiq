"""
Utility for mapping quantum measurement results to audio waveform data
Implements audio conversion that reflects quantum interference patterns
"""

import numpy as np
from scipy import signal
from typing import Dict, List, Tuple

from qwave.utils.constants import (
    SAMPLING_RATE, DEFAULT_DURATION, DEFAULT_ROOM_SIZE, 
    DEFAULT_ATTACK_TIME, DEFAULT_DECAY_TIME, DEFAULT_SUSTAIN_LEVEL, DEFAULT_RELEASE_TIME,
    BASE_FREQUENCY, HARMONIC_GAIN, MODULATION_FREQ_BASE, MODULATION_FREQ_OFFSET,
    AMPLITUDE_MOD_BASE, AMPLITUDE_MOD_RANGE, FM_WAVE_GAIN, FREQ_DEV_RANGE, FREQ_DEV_OFFSET
)


class QuantumAudioMapper:
    """Mapper that converts quantum measurement results to audio waveforms"""
    
    def __init__(self, sampling_rate: int = SAMPLING_RATE, duration: float = DEFAULT_DURATION):
        """
        Args:
            sampling_rate: Sampling frequency (Hz)
            duration: Audio length (seconds)
        """
        self.sampling_rate = sampling_rate
        self.duration = duration
        self.samples = int(sampling_rate * duration)
    
    def map_bitstring_to_amplitude(
        self, 
        bitstring: str, 
        use_interference: bool = True
    ) -> np.ndarray:
        """
        Map bitstring to amplitude data
        
        Args:
            bitstring: Quantum measurement result (e.g., '10110101')
            use_interference: Whether to apply quantum interference effects
            
        Returns:
            Amplitude data array
        """
        # Convert bitstring to integer
        value = int(bitstring, 2)
        max_value = 2 ** len(bitstring)
        
        # Normalize
        normalized = (value / max_value) * 2 - 1
        
        # Generate waveform
        t = np.linspace(0, self.duration, self.samples)
        
        if use_interference:
            # Simulate quantum interference patterns
            frequency = normalized * BASE_FREQUENCY  # Based on A4 note
            waveform = np.sin(2 * np.pi * frequency * t)
            
            # Multiple frequency interference patterns
            harmonics = np.zeros_like(t)
            for i in range(2, 6):  # Multiple harmonics
                phase = (value * i) % 256 / 256 * 2 * np.pi
                harmonics += (1/i) * np.sin(2 * np.pi * frequency * i * t + phase)
            
            waveform = waveform + HARMONIC_GAIN * harmonics
            waveform = self._apply_quantum_modulation(waveform, bitstring)
        else:
            # Simple sine wave
            frequency = 220 + normalized * 220
            waveform = np.sin(2 * np.pi * frequency * t)
        
        # Amplitude normalization
        waveform = waveform / np.max(np.abs(waveform)) * 0.8
        
        return waveform
    
    def _apply_quantum_modulation(
        self, 
        waveform: np.ndarray, 
        bitstring: str
    ) -> np.ndarray:
        """
        Apply quantum modulation (additional quantum interference pattern effects)
        
        Args:
            waveform: Base waveform
            bitstring: Quantum bitstring
            
        Returns:
            Modulated waveform
        """
        t = np.linspace(0, self.duration, len(waveform))
        
        # Modulation frequency based on bit pattern
        pattern_value = sum(int(bit) for bit in bitstring)
        mod_freq = pattern_value / len(bitstring) * MODULATION_FREQ_BASE + MODULATION_FREQ_OFFSET
        
        # Amplitude modulation
        amplitude_mod = AMPLITUDE_MOD_BASE + AMPLITUDE_MOD_RANGE * np.cos(2 * np.pi * mod_freq * t)
        
        # Frequency modulation
        freq_dev = (pattern_value % FREQ_DEV_RANGE) - FREQ_DEV_OFFSET  # -4 to +4
        fm_wave = np.sin(2 * np.pi * 0.5 * t * (1 + freq_dev * 0.1))
        
        modulated = waveform * amplitude_mod + FM_WAVE_GAIN * fm_wave
        
        return modulated
    
    def map_probability_distribution(
        self, 
        probability_dist: Dict[str, float],
        method: str = "weighted_sum"
    ) -> np.ndarray:
        """
        Generate audio waveform from probability distribution
        
        Args:
            probability_dist: Bitstring -> probability dictionary
            method: Synthesis method ('weighted_sum', 'stochastic').
            'stochastic' = probabilistic sampling from the quantum outcome
            distribution (not classical random generation).

        Returns:
            Integrated amplitude data
        """
        t = np.linspace(0, self.duration, self.samples)
        waveform = np.zeros(self.samples)
        
        if method == "weighted_sum":
            for bitstring, prob in probability_dist.items():
                if prob > 0.01:
                    amp = self.map_bitstring_to_amplitude(bitstring)
                    waveform += prob * amp
                    
        elif method == "stochastic":
            # Probabilistic sampling from quantum outcome distribution
            bitstrings = list(probability_dist.keys())
            probs = np.array(list(probability_dist.values()))
            probs = probs / np.sum(probs)
            
            # Sample based on probability at each time point
            for i in range(self.samples):
                selected = np.random.choice(bitstrings, p=probs)
                amp = self.map_bitstring_to_amplitude(selected)
                waveform[i] = amp[i]
        else:
            raise ValueError(f"Unknown method: {method}")
        
        # Normalize
        if np.max(np.abs(waveform)) > 0:
            waveform = waveform / np.max(np.abs(waveform)) * 0.8
        
        return waveform
    
    def apply_envelope(self, waveform: np.ndarray) -> np.ndarray:
        """
        Apply envelope (ADSR) to create natural sound
        
        Args:
            waveform: Original waveform
            
        Returns:
            Waveform with envelope applied
        """
        n_samples = len(waveform)
        
        # ADSR parameters
        attack_time = DEFAULT_ATTACK_TIME   # Attack time (seconds)
        decay_time = DEFAULT_DECAY_TIME     # Decay time (seconds)
        sustain_level = DEFAULT_SUSTAIN_LEVEL  # Sustain level
        release_time = DEFAULT_RELEASE_TIME   # Release time (seconds)
        
        # Convert to sample count
        attack_samples = int(attack_time * self.sampling_rate)
        decay_samples = int(decay_time * self.sampling_rate)
        release_samples = int(release_time * self.sampling_rate)
        
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
    
    def add_reverb(self, waveform: np.ndarray, room_size: float = DEFAULT_ROOM_SIZE) -> np.ndarray:
        """
        Add simple reverb effect
        
        Args:
            waveform: Original waveform
            room_size: Reverb size (0.0-1.0)
            
        Returns:
            Waveform with reverb applied
        """
        delay_samples = int(0.03 * self.sampling_rate * room_size)  # 30ms delay
        reverb_wave = np.zeros(len(waveform) + delay_samples)
        
        reverb_wave[:len(waveform)] = waveform
        reverb_wave[delay_samples:] += waveform * 0.3 * room_size
        
        return reverb_wave[:len(waveform)]
