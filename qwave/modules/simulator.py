"""
Quantum Circuit Simulator Module

This module handles loading quantum circuits from QASM files and executing
simulations to obtain measurement results and probability distributions.
Includes H2 (Quantinuum ion trap) style noise model and connectivity
benchmarking for NEDO grant pre-validation.

Supports local Aer simulation and remote execution via the IonQ provider.
"""

import logging
import os
from typing import Any, Callable, Dict, List, Optional

import numpy as np
from dotenv import load_dotenv
from qiskit import ClassicalRegister, QuantumCircuit, transpile
from qiskit.transpiler import CouplingMap
from qiskit_aer import Aer, AerSimulator
from qiskit_aer.noise import NoiseModel, depolarizing_error
from qiskit_ionq import IonQProvider

load_dotenv()

logger = logging.getLogger(__name__)

BACKEND_AER = "aer_simulator"
BACKEND_IONQ_SIMULATOR = "ionq_simulator"
BACKEND_IONQ_QPU = "ionq_qpu"

IONQ_BACKEND_NAMES = {
    BACKEND_IONQ_SIMULATOR: ("simulator", "ionq_simulator"),
    BACKEND_IONQ_QPU: ("qpu.forte-1", "ionq_qpu"),
}


def create_ion_trap_noise_model(
    two_qubit_error: float = 0.01,
    one_qubit_error: float = 0.001,
) -> NoiseModel:
    """
    Build a noise model approximating Quantinuum H2 (ion trap) characteristics.

    Adds depolarizing error primarily on 2-qubit gates to simulate ion-trap
    noise. Used for H2-style pre-validation in NEDO grant context.

    Args:
        two_qubit_error: Depolarizing error probability for 2-qubit gates (cx, cz).
        one_qubit_error: Optional single-qubit depolarizing error for realism.

    Returns:
        Qiskit NoiseModel instance.
    """
    noise_model = NoiseModel()
    error_2q = depolarizing_error(two_qubit_error, 2)
    noise_model.add_all_qubit_quantum_error(error_2q, ["cx", "cz"])
    if one_qubit_error > 0:
        error_1q = depolarizing_error(one_qubit_error, 1)
        noise_model.add_all_qubit_quantum_error(error_1q, ["u1", "u2", "u3", "h", "rx", "ry", "rz"])
    return noise_model


def _normalize_bitstring(bitstring: str, num_qubits: int) -> str:
    """Normalize IonQ/Aer count keys to a compact binary string."""
    cleaned = bitstring.replace(" ", "")
    if not cleaned:
        return "0" * num_qubits
    if all(ch in "01" for ch in cleaned):
        return cleaned.zfill(num_qubits)
    return cleaned


class QuantumSimulator:
    """
    Simulates quantum circuits and extracts measurement results for audio generation.

    This class loads quantum circuits from QASM files or QuantumCircuit objects,
    executes them on a local simulator or IonQ backends, and provides access to
    measurement results and probability distributions for audio generation.
    """

    def __init__(
        self,
        shots: int = 1024,
        backend_type: str = BACKEND_AER,
        status_callback: Optional[Callable[[str], None]] = None,
    ):
        """
        Initialize the quantum simulator.

        Args:
            shots: Number of measurement shots to execute (default: 1024)
            backend_type: Execution backend ('aer_simulator', 'ionq_simulator', 'ionq_qpu')
            status_callback: Optional callback for job status messages (e.g. GUI logging)
        """
        self.shots = shots
        self.requested_backend_type = backend_type
        self.backend_type = backend_type
        self.status_callback = status_callback
        self.backend_fallback_warning: Optional[str] = None
        self._ionq_provider: Optional[IonQProvider] = None
        self._using_ionq = False

        self.aer_backend = Aer.get_backend("qasm_simulator")
        self.statevector_backend = Aer.get_backend("statevector_simulator")
        self.backend = self.aer_backend

        self.circuit = None
        self.measurement_results = None
        self.probability_distribution = None
        self.statevector = None

        self._configure_shot_backend()

    def _emit_status(self, message: str) -> None:
        if self.status_callback is not None:
            self.status_callback(message)
        else:
            logger.info(message)

    def _is_ionq_backend_type(self, backend_type: str) -> bool:
        return backend_type in (BACKEND_IONQ_SIMULATOR, BACKEND_IONQ_QPU)

    def _get_ionq_backend(self, backend_type: str):
        if self._ionq_provider is None:
            api_key = os.getenv("IONQ_API_KEY")
            self._ionq_provider = IonQProvider(api_key) if api_key else IonQProvider()

        candidates = IONQ_BACKEND_NAMES.get(backend_type, ())
        last_error = None
        for name in candidates:
            try:
                return self._ionq_provider.get_backend(name)
            except Exception as exc:
                last_error = exc
        if last_error is not None:
            raise last_error
        raise ValueError(f"Unknown IonQ backend type: {backend_type}")

    def _configure_shot_backend(self) -> None:
        self.backend_fallback_warning = None
        self._using_ionq = False

        if not self._is_ionq_backend_type(self.backend_type):
            self.backend = self.aer_backend
            return

        api_key = os.getenv("IONQ_API_KEY")
        if not api_key:
            self.backend_fallback_warning = (
                "IONQ_API_KEY not found. Set it in a .env file or environment variables."
            )
            logger.warning(self.backend_fallback_warning)
            self.backend_type = BACKEND_AER
            self.backend = self.aer_backend
            return

        try:
            self.backend = self._get_ionq_backend(self.backend_type)
            self._using_ionq = True
        except Exception as exc:
            self.backend_fallback_warning = f"Failed to initialize IonQ backend: {exc}"
            logger.warning(self.backend_fallback_warning)
            self.backend_type = BACKEND_AER
            self.backend = self.aer_backend

    def set_backend_type(self, backend_type: str) -> Optional[str]:
        """
        Apply backend selection.

        Returns:
            Fallback warning message if IonQ could not be used, else None.
        """
        self.requested_backend_type = backend_type
        self.backend_type = backend_type
        self._configure_shot_backend()
        return self.backend_fallback_warning

    def get_backend_status(self) -> Dict[str, Optional[str]]:
        """Return requested/effective backend info for UI display."""
        effective = "ionq" if self._using_ionq else BACKEND_AER
        return {
            "requested": self.requested_backend_type,
            "effective": self.backend_type if self._using_ionq else BACKEND_AER,
            "effective_label": effective,
            "warning": self.backend_fallback_warning,
        }

    def _normalize_counts(self, counts: Dict[str, int]) -> Dict[str, int]:
        if self.circuit is None:
            return counts
        num_qubits = self.circuit.num_qubits
        normalized: Dict[str, int] = {}
        for bitstring, count in counts.items():
            key = _normalize_bitstring(str(bitstring), num_qubits)
            normalized[key] = normalized.get(key, 0) + count
        return normalized

    def _execute_ionq_simulation(self, shot_circuit: QuantumCircuit) -> Dict[str, int]:
        job = self.backend.run(shot_circuit, shots=self.shots)
        job_id = job.job_id()
        self._emit_status(f"IonQ job submitted: {job_id}")

        last_status = None

        def status_callback(job_id_cb, job_status, _job):
            nonlocal last_status
            status_str = str(job_status)
            if status_str != last_status:
                last_status = status_str
                self._emit_status(f"IonQ job {job_id_cb}: {status_str}")

        result = job.result(callback=status_callback, wait=5)
        counts = result.get_counts()
        if isinstance(counts, list):
            counts = counts[0]
        self.measurement_results = self._normalize_counts(counts)
        self._emit_status(f"IonQ job {job_id} completed.")
        return self.measurement_results

    def _circuit_for_shots(self) -> QuantumCircuit:
        """
        Return a circuit suitable for shot-based simulation with counts.

        QASM / GUI circuits may have classical registers but no measure gates;
        Aer then returns no counts. In that case we measure every qubit in the
        computational basis (qubit i -> classical bit i). If there are no
        classical bits, a register is added first.
        """
        qc = self.circuit.copy()
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

    def load_circuit_from_qasm(self, qasm_file_path: str) -> QuantumCircuit:
        """
        Load a quantum circuit from a QASM file.

        Args:
            qasm_file_path: Path to the QASM file

        Returns:
            Loaded QuantumCircuit object

        Raises:
            FileNotFoundError: If the QASM file doesn't exist
            ValueError: If the QASM file is invalid
        """
        if not os.path.exists(qasm_file_path):
            raise FileNotFoundError(f"QASM file not found: {qasm_file_path}")

        try:
            self.circuit = QuantumCircuit.from_qasm_file(qasm_file_path)
            return self.circuit
        except Exception as e:
            raise ValueError(f"Failed to load QASM file: {e}") from e

    def load_circuit(self, circuit: QuantumCircuit) -> QuantumCircuit:
        """
        Load a quantum circuit from a QuantumCircuit object.

        Args:
            circuit: QuantumCircuit object to load

        Returns:
            The loaded QuantumCircuit object
        """
        self.circuit = circuit
        return self.circuit

    def execute_simulation(
        self,
        noise_model: Optional[NoiseModel] = None,
        backend_type: Optional[str] = None,
    ) -> Dict[str, int]:
        """
        Execute the loaded quantum circuit and obtain measurement results.

        Optionally run with an H2-style noise model (e.g. from create_ion_trap_noise_model).

        Args:
            noise_model: Optional NoiseModel for noisy simulation (e.g. ion trap).
            backend_type: Optional override for the configured backend type.

        Returns:
            Dictionary mapping measurement bitstrings to their counts

        Raises:
            RuntimeError: If no circuit is loaded
        """
        if self.circuit is None:
            raise RuntimeError("No circuit loaded. Call load_circuit_from_qasm() or load_circuit() first.")

        if backend_type is not None and backend_type != self.backend_type:
            previous_type = self.backend_type
            self.set_backend_type(backend_type)
            try:
                return self.execute_simulation(noise_model=noise_model)
            finally:
                self.set_backend_type(previous_type)

        shot_circuit = self._circuit_for_shots()

        if noise_model is not None:
            backend = AerSimulator(noise_model=noise_model)
            job = backend.run(shot_circuit, shots=self.shots)
            result = job.result()
            self.measurement_results = self._normalize_counts(result.get_counts())
            return self.measurement_results

        if self._using_ionq:
            return self._execute_ionq_simulation(shot_circuit)

        job = self.backend.run(shot_circuit, shots=self.shots)
        result = job.result()
        self.measurement_results = self._normalize_counts(result.get_counts())
        return self.measurement_results

    def get_statevector(self) -> np.ndarray:
        """
        Get the statevector representation of the quantum circuit.

        This provides access to the full quantum state including phase information,
        which is crucial for capturing quantum interference patterns.

        IonQ backends do not expose statevectors; when IonQ is selected for shots,
        the statevector is computed locally via Aer.

        Returns:
            Complex numpy array representing the quantum statevector

        Raises:
            RuntimeError: If no circuit is loaded
        """
        if self.circuit is None:
            raise RuntimeError("No circuit loaded. Call load_circuit_from_qasm() or load_circuit() first.")

        if self._using_ionq:
            self._emit_status(
                "Computing statevector locally (Aer); measurement shots use IonQ."
            )

        job = self.statevector_backend.run(self.circuit)
        result = job.result()
        statevector_obj = result.get_statevector()

        self.statevector = np.asarray(statevector_obj)
        return self.statevector

    def get_probability_distribution(self) -> np.ndarray:
        """
        Calculate the probability distribution from measurement results.

        Returns:
            Normalized probability array for each possible measurement outcome
        """
        if self.measurement_results is None:
            self.execute_simulation()

        if self.circuit is None:
            raise RuntimeError("No circuit loaded.")

        num_qubits = self.circuit.num_qubits
        num_states = 2 ** num_qubits

        probabilities = np.zeros(num_states)

        for bitstring, count in self.measurement_results.items():
            state_index = int(bitstring, 2)
            probabilities[state_index] = count / self.shots

        self.probability_distribution = probabilities
        return probabilities

    def get_measurement_sequence(self) -> List[int]:
        """
        Probabilistic sampling from the quantum outcome distribution.

        Generates a time-ordered sequence of measurement outcomes by sampling
        according to the circuit's probability distribution (not classical
        random generation). Used for audio waveform generation.

        Returns:
            List of measurement outcome indices
        """
        if self.probability_distribution is None:
            self.get_probability_distribution()

        num_states = len(self.probability_distribution)
        sequence = np.random.choice(
            num_states,
            size=self.shots,
            p=self.probability_distribution,
        )

        return sequence.tolist()

    def get_circuit_info(self) -> Dict[str, any]:
        """
        Get information about the loaded quantum circuit.

        Returns:
            Dictionary containing circuit metadata
        """
        if self.circuit is None:
            return {}

        return {
            "num_qubits": self.circuit.num_qubits,
            "num_clbits": self.circuit.num_clbits,
            "depth": self.circuit.depth(),
            "size": self.circuit.size(),
            "gates": [gate[0].name for gate in self.circuit.data],
        }

    def benchmark_connectivity(self, circuit: QuantumCircuit) -> Dict[str, Any]:
        """
        Compare circuit cost under all-to-all (H2-style) vs linear connectivity.

        Transpiles the circuit twice and returns depth and CNOT counts for
        NEDO pre-validation evidence (why H2 all-to-all is beneficial).

        Args:
            circuit: Circuit to benchmark (will not be modified).

        Returns:
            Dict with depth_all_to_all, depth_linear, cnot_all_to_all,
            cnot_linear, depth_delta, cnot_delta.
        """
        n = circuit.num_qubits
        transpiled_aa = transpile(circuit, coupling_map=None, optimization_level=1)
        depth_aa = transpiled_aa.depth()
        cnot_aa = transpiled_aa.count_ops().get("cx", 0) + transpiled_aa.count_ops().get("cz", 0)

        linear_edges = [(i, i + 1) for i in range(n - 1)]
        coupling_linear = CouplingMap(linear_edges)
        transpiled_linear = transpile(
            circuit,
            coupling_map=coupling_linear,
            optimization_level=1,
        )
        depth_linear = transpiled_linear.depth()
        cnot_linear = transpiled_linear.count_ops().get("cx", 0) + transpiled_linear.count_ops().get("cz", 0)

        result = {
            "depth_all_to_all": depth_aa,
            "depth_linear": depth_linear,
            "cnot_all_to_all": cnot_aa,
            "cnot_linear": cnot_linear,
            "depth_delta": depth_linear - depth_aa,
            "cnot_delta": cnot_linear - cnot_aa,
        }
        print(
            "[Connectivity benchmark] All-to-all (H2): depth={}, CNOT={} | "
            "Linear: depth={}, CNOT={} | Delta: depth={}, CNOT={}".format(
                depth_aa,
                cnot_aa,
                depth_linear,
                cnot_linear,
                result["depth_delta"],
                result["cnot_delta"],
            )
        )
        return result
