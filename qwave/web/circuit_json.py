"""Build Qiskit circuits from JSON payloads sent by the web UI."""

from __future__ import annotations

from typing import Any, Dict, List

from qiskit import QuantumCircuit


GATE_ALIASES = {
    "CX": "CNOT",
    "MEASURE": "M",
}


def _normalize_gate_type(gate_type: str) -> str:
    normalized = gate_type.strip().upper()
    return GATE_ALIASES.get(normalized, normalized)


def circuit_from_payload(payload: Dict[str, Any]) -> QuantumCircuit:
    """
    Convert a web UI circuit payload into a QuantumCircuit.

    Expected shape:
    {
      "num_qubits": 3,
      "gates": [
        {"column": 0, "type": "H", "qubit": 0},
        {"column": 0, "type": "CNOT", "control": 0, "target": 1}
      ]
    }
    """
    num_qubits = int(payload.get("num_qubits", 2))
    gates: List[Dict[str, Any]] = list(payload.get("gates") or [])

    if num_qubits < 1:
        raise ValueError("num_qubits must be at least 1")

    circuit = QuantumCircuit(num_qubits, num_qubits)
    sorted_gates = sorted(gates, key=lambda gate: (gate.get("column", 0), gate.get("type", "")))

    applied_two_qubit: set[tuple[int, str, int, int]] = set()

    for gate in sorted_gates:
        gate_type = _normalize_gate_type(str(gate.get("type", "")))
        column = int(gate.get("column", 0))

        if gate_type in {"H", "X", "Y", "Z", "T", "S"}:
            qubit = int(gate["qubit"])
            getattr(circuit, gate_type.lower())(qubit)
        elif gate_type == "M":
            qubit = int(gate["qubit"])
            circuit.measure(qubit, qubit)
        elif gate_type in {"CNOT", "CZ"}:
            control = int(gate["control"])
            target = int(gate["target"])
            key = (column, gate_type, control, target)
            if key in applied_two_qubit:
                continue
            applied_two_qubit.add(key)
            if gate_type == "CNOT":
                circuit.cx(control, target)
            else:
                circuit.cz(control, target)
        else:
            raise ValueError(f"Unsupported gate type: {gate_type}")

    return circuit
