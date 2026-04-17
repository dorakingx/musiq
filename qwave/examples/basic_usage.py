#!/usr/bin/env python3
"""
Basic Usage Example for Q-Wave

Demonstrates how to use Q-Wave modules to generate quantum audio.
"""

import numpy as np
from qiskit import QuantumCircuit
from pathlib import Path

from qwave.modules.simulator import QuantumSimulator
from qwave.modules.generator import AudioGenerator
from qwave.modules.analyzer import SpectralAnalyzer
from qwave.utils.constants import SAMPLING_RATE, DEFAULT_DURATION, DEFAULT_SHOTS


def main():
    """Generate quantum audio from a simple circuit."""
    
    # Create a simple quantum circuit
    print("Creating quantum circuit...")
    circuit = QuantumCircuit(5)
    circuit.h(range(5))  # Create superposition
    circuit.cz(0, 1)      # Entangle qubits
    circuit.cz(1, 2)
    circuit.cz(2, 3)
    circuit.cz(3, 4)
    circuit.h(range(5))   # Final Hadamard for interference
    circuit.measure_all()
    
    # Simulate the circuit
    print("Simulating quantum circuit...")
    simulator = QuantumSimulator(shots=DEFAULT_SHOTS)
    simulator.load_circuit(circuit)
    statevector = simulator.get_statevector()
    measurement_sequence = simulator.get_measurement_sequence()
    probability_dist = simulator.get_probability_distribution()
    
    print(f"Circuit info: {simulator.get_circuit_info()}")
    
    # Generate audio
    print("Generating audio waveform...")
    generator = AudioGenerator(sample_rate=SAMPLING_RATE)
    waveform = generator.map_quantum_to_audio(
        statevector=statevector,
        measurement_sequence=measurement_sequence,
        probability_distribution=probability_dist,
        duration=DEFAULT_DURATION,
        apply_envelope=True,
        apply_reverb=False
    )
    
    # Save audio
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / "basic_example.wav"
    generator.save_wav(waveform, str(output_file))
    print(f"Audio saved to: {output_file}")
    
    # Analyze the generated audio
    print("Analyzing audio...")
    analyzer = SpectralAnalyzer(sample_rate=SAMPLING_RATE)
    results = analyzer.analyze(waveform)
    
    print("\nAnalysis Results:")
    print("=" * 50)
    analyzer.print_analysis_report(results)
    
    print("Example completed successfully!")


if __name__ == "__main__":
    main()





