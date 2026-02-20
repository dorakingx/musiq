#!/usr/bin/env python3
"""
Variational Circuit Example

Demonstrates building a parameterized (variational) quantum circuit in code,
simulating it, and generating audio. No static QASM files; circuits are
generated dynamically using variational forms (ansatz) for NEDO quantum
optimization alignment.
"""

import numpy as np
from pathlib import Path
from qiskit import QuantumCircuit
from qiskit.circuit.library import RealAmplitudes

from qwave.modules.simulator import QuantumSimulator
from qwave.modules.generator import AudioGenerator
from qwave.utils.constants import SAMPLING_RATE, DEFAULT_DURATION, DEFAULT_SHOTS


def build_variational_circuit(n_qubits: int = 4, reps: int = 2) -> QuantumCircuit:
    """
    Build a parameterized variational circuit (ansatz) for audio generation.

    Uses RealAmplitudes as a simple VQE-style ansatz. Parameters are bound
    to initial values before execution (e.g. for probabilistic sampling from
    the resulting quantum distribution).
    """
    ansatz = RealAmplitudes(n_qubits, reps=reps)
    # Bind parameters to initial values (variational initialization)
    num_params = ansatz.num_parameters
    initial_params = np.linspace(0.1, 0.9, num_params)
    circuit = ansatz.assign_parameters(initial_params)
    circuit.measure_all()
    return circuit


def main():
    """Build a variational circuit, simulate it, and generate audio."""
    n_qubits = 4
    print("Building variational circuit (RealAmplitudes ansatz)...")
    circuit = build_variational_circuit(n_qubits=n_qubits)

    print(f"Circuit: {circuit.num_qubits} qubits, depth={circuit.depth()}, size={circuit.size()}")

    simulator = QuantumSimulator(shots=DEFAULT_SHOTS)
    simulator.load_circuit(circuit)

    # Optional: print connectivity benchmark (H2 vs linear)
    simulator.benchmark_connectivity(circuit)

    print("Running simulation...")
    simulator.execute_simulation()
    statevector = simulator.get_statevector()
    measurement_sequence = simulator.get_measurement_sequence()

    print(f"Generated {len(measurement_sequence)} measurement outcomes (probabilistic sampling)")

    print("Generating audio (with interference mode)...")
    generator = AudioGenerator(sample_rate=SAMPLING_RATE)
    waveform = generator.map_quantum_to_audio(
        statevector=statevector,
        measurement_sequence=measurement_sequence,
        duration=DEFAULT_DURATION,
        apply_envelope=True,
        apply_reverb=True,
        interference_mode=True,
    )

    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / "variational_example.wav"
    generator.save_wav(waveform, str(output_file))

    print(f"Audio saved to: {output_file}")
    print("Example completed successfully!")


if __name__ == "__main__":
    main()
