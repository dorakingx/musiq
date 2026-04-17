#!/usr/bin/env python3
"""
Generate large-scale OpenQASM 2.0 circuits for quantum-advantage-style experiments
(quantum walks, IQP) and write them under the repository root ``circuits/``
directory (alongside other sample QASM files).

IQP circuits are transpiled to a gate set compatible with the GUI
(``qwave.gui.circuit_builder.CircuitBuilderWidget``) before export.
"""

from __future__ import annotations

import math
import random
from pathlib import Path

from qiskit import QuantumCircuit, transpile
from qiskit.qasm2 import dumps

from qwave.scripts.verify_quantum_walk import build_quantum_walk_circuit

# Gates the visual builder can reconstruct (plus ``cx`` → CNOT mapping)
_EXPORT_BASIS = ["h", "cz", "t", "s", "z", "x", "y", "cx"]


def build_iqp_circuit(num_qubits: int, depth: int) -> QuantumCircuit:
    """
    IQP-style circuit for interference benchmarks.

    Structure:
        1. Hadamard layer on all qubits.
        2. ``depth`` layers: random disjoint pairs get ``cz`` or ``rzz``; optional
           ``t`` / ``s`` / ``z`` on random qubits for diagonal phase.
        3. Final Hadamard layer.
        4. Measurement on all qubits.

    Args:
        num_qubits: Number of quantum (and classical) bits.
        depth: Number of entangling layers.

    Returns:
        A ``QuantumCircuit`` with terminal measurements.
    """
    qc = QuantumCircuit(num_qubits, num_qubits)
    theta_choices = [math.pi / 4, math.pi / 2, math.pi / 3]

    qc.h(range(num_qubits))

    for _ in range(depth):
        indices = list(range(num_qubits))
        random.shuffle(indices)
        # Disjoint pairs covering all qubits (num_qubits must be even)
        for i in range(0, num_qubits - 1, 2):
            a, b = indices[i], indices[i + 1]
            if random.random() < 0.5:
                qc.cz(a, b)
            else:
                theta = random.choice(theta_choices)
                qc.rzz(theta, a, b)
        for q in range(num_qubits):
            if random.random() < 0.3:
                random.choice((qc.t, qc.s, qc.z))(q)

    qc.h(range(num_qubits))
    qc.measure(range(num_qubits), range(num_qubits))
    return qc


def _transpile_for_gui_export(qc: QuantumCircuit) -> QuantumCircuit:
    """Map to a basis the GUI can load (H, CZ, T, S, Z, X, Y, CX)."""
    return transpile(
        qc,
        basis_gates=_EXPORT_BASIS,
        optimization_level=1,
        seed_transpiler=42,
    )


def _repo_root() -> Path:
    """Parent of the ``qwave`` package (repository root in a source checkout)."""
    return Path(__file__).resolve().parent.parent.parent


def main() -> None:
    random.seed(42)
    out_dir = _repo_root() / "circuits"
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"Output directory: {out_dir}\n")

    qw_specs = [
        ("quantum_walk_8q.qasm", 14, 7),
        ("quantum_walk_16q.qasm", 30, 15),
        ("quantum_walk_20q.qasm", 42, 19),
        ("quantum_walk_24q.qasm", 50, 23),
        ("quantum_walk_56q.qasm", 110, 55),
    ]
    for filename, steps, n_pos in qw_specs:
        qc = build_quantum_walk_circuit(steps=steps, num_qubits=n_pos)
        path = out_dir / filename
        path.write_text(dumps(qc), encoding="utf-8")
        total = qc.num_qubits
        print(
            f"[OK] {path}  "
            f"(quantum walk: total_qubits={total}, steps={steps}, position_qubits={n_pos})"
        )

    iqp_specs = [
        ("iqp_8q.qasm", 8, 4),
        ("iqp_16q.qasm", 16, 5),
        ("iqp_20q.qasm", 20, 7),
        ("iqp_24q.qasm", 24, 8),
        ("iqp_56q.qasm", 56, 10),
    ]
    for filename, nq, depth in iqp_specs:
        qc = build_iqp_circuit(num_qubits=nq, depth=depth)
        tqc = _transpile_for_gui_export(qc)
        path = out_dir / filename
        path.write_text(dumps(tqc), encoding="utf-8")
        print(
            f"[OK] {path}  "
            f"(IQP: num_qubits={nq}, depth={depth}, transpiled_ops={tqc.size()})"
        )

    print("\nAll advantage-scale QASM files generated successfully.")


if __name__ == "__main__":
    main()
