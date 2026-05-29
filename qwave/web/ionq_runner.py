"""IonQ cloud execution for the web API (no qiskit-aer dependency)."""

from __future__ import annotations

import os
import time
from typing import Callable, Dict, List, Optional, Tuple

from qiskit import ClassicalRegister, QuantumCircuit
from qiskit_ionq import IonQProvider

from qwave.utils.backends import (
    BACKEND_AER,
    BACKEND_IONQ_QPU,
    BACKEND_IONQ_SIMULATOR,
    get_backend_label,
)

IONQ_BACKEND_NAMES = {
    BACKEND_IONQ_SIMULATOR: ("simulator", "ionq_simulator"),
    BACKEND_IONQ_QPU: ("qpu.forte-1", "ionq_qpu"),
}

IONQ_TERMINAL_STATUSES = {"DONE", "ERROR", "CANCELLED"}


def _normalize_bitstring(bitstring: str, num_qubits: int) -> str:
    cleaned = bitstring.replace(" ", "")
    if not cleaned:
        return "0" * num_qubits
    if all(ch in "01" for ch in cleaned):
        return cleaned.zfill(num_qubits)
    return cleaned


def _circuit_for_shots(circuit: QuantumCircuit) -> QuantumCircuit:
    qc = circuit.copy()
    has_measure = any(getattr(inst.operation, "name", "") == "measure" for inst in qc.data)
    if has_measure:
        return qc
    n = qc.num_qubits
    if n == 0:
        return qc
    if qc.num_clbits == 0:
        qc.add_register(ClassicalRegister(n, "meas"))
        for i in range(n):
            qc.measure(i, i)
    elif qc.num_clbits >= n:
        for i in range(n):
            qc.measure(i, i)
    else:
        qc.measure_all()
    return qc


def _get_ionq_backend(backend_type: str, api_key: str):
    provider = IonQProvider(api_key)
    candidates = IONQ_BACKEND_NAMES.get(backend_type, ())
    last_error = None
    for name in candidates:
        try:
            return provider.get_backend(name)
        except Exception as exc:
            last_error = exc
    if last_error is not None:
        raise last_error
    raise ValueError(f"Unknown IonQ backend type: {backend_type}")


def _ionq_status_name(job_status) -> str:
    status_str = str(job_status)
    if "." in status_str:
        return status_str.rsplit(".", 1)[-1]
    return status_str


def run_ionq_shots(
    circuit: QuantumCircuit,
    shots: int,
    backend_type: str,
    status_callback: Optional[Callable[[str], None]] = None,
) -> Dict[str, int]:
    """Submit circuit to IonQ and return measurement counts."""
    api_key = os.getenv("IONQ_API_KEY")
    if not api_key:
        raise RuntimeError("IONQ_API_KEY is not configured.")

    def emit(message: str) -> None:
        if status_callback is not None:
            status_callback(message)

    backend = _get_ionq_backend(backend_type, api_key)
    shot_circuit = _circuit_for_shots(circuit)
    job = backend.run(shot_circuit, shots=shots)
    job_id = job.job_id()
    emit(f"IonQ job submitted: {job_id}")

    last_status = None
    final_status_name = None
    poll_interval_seconds = 5

    while True:
        job_status = job.status()
        status_name = _ionq_status_name(job_status)
        if status_name != last_status:
            last_status = status_name
            emit(f"IonQ job {job_id}: {job_status}")

        if status_name in IONQ_TERMINAL_STATUSES:
            final_status_name = status_name
            break

        time.sleep(poll_interval_seconds)

    if final_status_name == "CANCELLED":
        raise RuntimeError(f"IonQ job {job_id} was cancelled.")
    if final_status_name == "ERROR":
        raise RuntimeError(f"IonQ job {job_id} failed with status {last_status}.")

    result = job.result()
    counts = result.get_counts()
    if isinstance(counts, list):
        counts = counts[0]

    num_qubits = circuit.num_qubits
    normalized: Dict[str, int] = {}
    for bitstring, count in counts.items():
        key = _normalize_bitstring(str(bitstring), num_qubits)
        normalized[key] = normalized.get(key, 0) + count

    emit(f"IonQ job {job_id} completed.")
    return normalized


def resolve_ionq_backend(
    backend_type: str,
) -> Tuple[str, Optional[str], str]:
    """
    Resolve whether IonQ can run.

    Returns:
        effective backend type, optional fallback warning, effective label
    """
    if backend_type not in (BACKEND_IONQ_SIMULATOR, BACKEND_IONQ_QPU):
        return backend_type, None, get_backend_label(backend_type)

    if not os.getenv("IONQ_API_KEY"):
        warning = (
            "IONQ_API_KEY not found. Set it in Vercel Environment Variables "
            "or a local .env file."
        )
        return BACKEND_AER, warning, get_backend_label(BACKEND_AER)

    return backend_type, None, get_backend_label(backend_type)
