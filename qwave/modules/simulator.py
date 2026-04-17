"""
Quantum Circuit Simulator Module

This module handles loading quantum circuits from QASM files and executing
simulations to obtain measurement results and probability distributions.
Includes H2 (Quantinuum ion trap) style noise model and connectivity
benchmarking for NEDO grant pre-validation.
"""

import numpy as np
from qiskit import QuantumCircuit, ClassicalRegister, transpile
from qiskit_aer import Aer, AerSimulator
from qiskit_aer.noise import NoiseModel, depolarizing_error
from qiskit.transpiler import CouplingMap
from qiskit.quantum_info import Statevector
from typing import Dict, List, Optional, Any
import os


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


class QuantumSimulator:
    """
    Simulates quantum circuits and extracts measurement results for audio generation.
    
    This class loads quantum circuits from QASM files or QuantumCircuit objects,
    executes them on a local simulator, and provides access to measurement results
    and probability distributions that will be used to generate non-classical audio patterns.
    """
    
    def __init__(self, shots: int = 1024):
        """
        Initialize the quantum simulator.
        
        Args:
            shots: Number of measurement shots to execute (default: 1024)
        """
        self.shots = shots
        self.backend = Aer.get_backend('qasm_simulator')
        self.statevector_backend = Aer.get_backend('statevector_simulator')
        self.circuit = None
        self.measurement_results = None
        self.probability_distribution = None
        self.statevector = None

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
            raise ValueError(f"Failed to load QASM file: {e}")
    
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
    ) -> Dict[str, int]:
        """
        Execute the loaded quantum circuit and obtain measurement results.

        Optionally run with an H2-style noise model (e.g. from create_ion_trap_noise_model).

        Args:
            noise_model: Optional NoiseModel for noisy simulation (e.g. ion trap).

        Returns:
            Dictionary mapping measurement bitstrings to their counts

        Raises:
            RuntimeError: If no circuit is loaded
        """
        if self.circuit is None:
            raise RuntimeError("No circuit loaded. Call load_circuit_from_qasm() or load_circuit() first.")

        shot_circuit = self._circuit_for_shots()
        if noise_model is not None:
            backend = AerSimulator(noise_model=noise_model)
            job = backend.run(shot_circuit, shots=self.shots)
        else:
            job = self.backend.run(shot_circuit, shots=self.shots)
        result = job.result()
        self.measurement_results = result.get_counts()

        return self.measurement_results
    
    def get_statevector(self) -> np.ndarray:
        """
        Get the statevector representation of the quantum circuit.
        
        This provides access to the full quantum state including phase information,
        which is crucial for capturing quantum interference patterns.
        
        Returns:
            Complex numpy array representing the quantum statevector
            
        Raises:
            RuntimeError: If no circuit is loaded
        """
        if self.circuit is None:
            raise RuntimeError("No circuit loaded. Call load_circuit_from_qasm() or load_circuit() first.")
        
        # Execute statevector simulation
        job = self.statevector_backend.run(self.circuit)
        result = job.result()
        statevector_obj = result.get_statevector()
        
        # Convert Statevector object to numpy array
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
        
        # Initialize probability array
        probabilities = np.zeros(num_states)
        
        # Fill in probabilities from measurement results
        for bitstring, count in self.measurement_results.items():
            # Convert bitstring to integer index
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
        
        # Generate sequence by sampling from the distribution
        num_states = len(self.probability_distribution)
        sequence = np.random.choice(
            num_states,
            size=self.shots,
            p=self.probability_distribution
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
            'num_qubits': self.circuit.num_qubits,
            'num_clbits': self.circuit.num_clbits,
            'depth': self.circuit.depth(),
            'size': self.circuit.size(),
            'gates': [gate[0].name for gate in self.circuit.data]
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
        # All-to-all: no coupling map (H2-style)
        transpiled_aa = transpile(circuit, coupling_map=None, optimization_level=1)
        depth_aa = transpiled_aa.depth()
        cnot_aa = transpiled_aa.count_ops().get("cx", 0) + transpiled_aa.count_ops().get("cz", 0)

        # Linear coupling map (standard superconducting style)
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
                depth_aa, cnot_aa, depth_linear, cnot_linear,
                result["depth_delta"], result["cnot_delta"],
            )
        )
        return result





