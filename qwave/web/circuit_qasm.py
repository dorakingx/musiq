"""QASM import/export for the web UI (parity with desktop circuit builder)."""

from __future__ import annotations

from typing import Any, Dict, List

from qiskit import QuantumCircuit
from qiskit.qasm2 import dumps, loads

from qwave.web.circuit_json import circuit_from_payload

SUPPORTED_GATES = {"H", "X", "Y", "Z", "T", "S", "CNOT", "CZ", "M", "CX"}


def export_qasm_from_payload(payload: Dict[str, Any]) -> str:
    circuit = circuit_from_payload(payload)
    return dumps(circuit)


def import_gates_from_qasm(qasm: str) -> Dict[str, Any]:
    """Convert OpenQASM 2 text into web UI gate list (visual column layout)."""
    circuit = loads(qasm)
    num_qubits = circuit.num_qubits
    gates: List[Dict[str, Any]] = []
    qubit_columns = {i: 0 for i in range(num_qubits)}

    for instruction in circuit.data:
        gate_name = instruction.operation.name.upper()
        gate_map = {"CX": "CNOT", "MEASURE": "M"}
        gui_gate_name = gate_map.get(gate_name, gate_name)
        if gui_gate_name not in SUPPORTED_GATES:
            continue

        qubits = [circuit.find_bit(q).index for q in instruction.qubits]

        if len(qubits) == 1:
            q = qubits[0]
            col = qubit_columns[q]
            gates.append({"column": col, "type": gui_gate_name, "qubit": q})
            qubit_columns[q] = col + 1
        elif len(qubits) == 2:
            q_ctrl, q_tgt = qubits[0], qubits[1]
            col = max(qubit_columns[q_ctrl], qubit_columns[q_tgt])
            gates.append(
                {
                    "column": col,
                    "type": gui_gate_name,
                    "control": q_ctrl,
                    "target": q_tgt,
                }
            )
            qubit_columns[q_ctrl] = col + 1
            qubit_columns[q_tgt] = col + 1

    return {"num_qubits": num_qubits, "gates": gates}
