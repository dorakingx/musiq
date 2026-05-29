"""Lightweight ideal simulation for serverless web deployment (no qiskit-aer)."""

from __future__ import annotations

from typing import Dict, List, Tuple

import numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector


def _circuit_without_measurements(circuit: QuantumCircuit) -> QuantumCircuit:
    qc = circuit.copy()
    qc.data = [
        instruction
        for instruction in qc.data
        if getattr(instruction.operation, "name", "") != "measure"
    ]
    return qc


def simulate_ideal(
    circuit: QuantumCircuit,
    shots: int,
) -> Tuple[np.ndarray, List[int], np.ndarray]:
    """
    Run ideal statevector simulation and derive shot statistics locally.

    Returns:
        statevector, measurement_sequence, probability_distribution
    """
    ideal_circuit = _circuit_without_measurements(circuit)
    statevector = np.asarray(Statevector(ideal_circuit))
    num_states = len(statevector)

    probabilities = np.abs(statevector) ** 2
    probabilities = probabilities / (probabilities.sum() or 1.0)

    measurement_sequence = np.random.choice(
        num_states,
        size=shots,
        p=probabilities,
    ).tolist()

    return statevector, measurement_sequence, probabilities
