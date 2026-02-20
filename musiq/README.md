# Q-Wave: Quantum Music Generation Platform

## Project Overview

Q-Wave is a quantum music generation platform that generates waveforms with new acoustic structures using quantum circuits. It explores novel acoustic patterns that cannot be captured by traditional music theory using quantum interference and optimization algorithms.

## Key Features

### Module A: Quantum Waveform Generation Core (QASM → WAV conversion)
- Execution of random quantum circuits and boson sampling systems
- Mapping quantum measurement results to audio waveforms
- WAV format output (standard sampling frequency: 44100 Hz)

### Module B: Quantum Optimization and Music Structure Design
- Quantum optimization using VQE/QAOA
- Music structure exploration and parameter optimization
- Design based on emotions, genres, and acoustic indicators

### Module C: Analysis and GUI Integration
- Spectrogram analysis and visualization
- Audio feature analysis
- Intuitive GUI interface

## Installation

```bash
# Clone repository
git clone <repository-url>
cd Q-Wave

# Install dependencies
pip install -r requirements.txt
```

## Usage Examples

### Basic Usage (Python API)

```python
from qwave.modules import QuantumWaveformGenerator, QuantumOptimizer, AudioAnalyzer

# Generate quantum waveform
generator = QuantumWaveformGenerator(n_qubits=8, duration=2.0)
quantum_wave = generator.generate_waveform(
    circuit_type='random',
    output_file="quantum_sound.wav"
)

# Music structure design through quantum optimization
optimizer = QuantumOptimizer()
optimized_wave = optimizer.optimize_music_structure(
    target_emotion="energetic",
    output_file="optimized_sound.wav"
)

# Audio analysis
analyzer = AudioAnalyzer()
waveform, _ = analyzer.load_audio("quantum_sound.wav")
features = analyzer.analyze_audio_features(waveform)
```

### GUI Application

```bash
python run_gui.py
```

### Sample Script Execution

```bash
python examples/basic_usage.py
```

## Project Structure

```
Q-Wave/
├── qwave/
│   ├── modules/
│   │   ├── quantum_waveform_generator.py  # Module A
│   │   ├── quantum_optimizer.py           # Module B
│   │   └── audio_analyzer.py              # Module C-1
│   ├── gui/
│   │   └── main_window.py                 # Module C-2
│   └── utils/
│       └── quantum_audio_mapper.py
├── examples/
│   └── basic_usage.py                     # Usage examples
├── output/                                # Output directory
├── requirements.txt                       # Dependencies
└── README.md
```

## Feature Details

### Quantum Circuit Types

- **random**: Random quantum circuits
- **boson_sampling**: Boson sampling-style circuits
- **iqp**: IQP circuits (expected quantum advantage)

### Target Emotions for Optimization

- **energetic**: Energetic sound
- **calm**: Calm sound
- **mysterious**: Mysterious sound
- **happy**: Bright sound

### Audio Features

- Spectral entropy
- Spectral centroid
- Temporal modulation characteristics
- Scale invariance
- Others

## Notes

- Quantum circuit execution requires computational resources
- Proper authentication is required when using actual quantum devices
- Execution time may increase with larger qubit counts

## License

MIT License

## References

- Qiskit Documentation: https://qiskit.org/
- Research on quantum computing and music generation
