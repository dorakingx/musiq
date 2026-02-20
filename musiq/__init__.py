"""
Q-Wave: Quantum Music Generation Platform

A unified platform for generating non-classical audio patterns from quantum circuits.
"""

__version__ = "1.0.0"

from qwave.modules import (
    QuantumSimulator,
    AudioGenerator,
    SpectralAnalyzer,
    QuantumOptimizer,
)
from qwave.gui import QWaveGUI, main

__all__ = [
    'QuantumSimulator',
    'AudioGenerator',
    'SpectralAnalyzer',
    'QuantumOptimizer',
    'QWaveGUI',
    'main',
]
