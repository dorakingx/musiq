"""
Module B: Quantum Optimization and Music Structure Design
Utilizing quantum variational algorithms (VQE/QAOA) to explore and optimize music structures
"""

import numpy as np
from qiskit import QuantumCircuit, Aer, execute
from qiskit.algorithms import VQE, QAOA
from qiskit.algorithms.optimizers import SPSA, COBYLA
from qiskit.circuit.library import RealAmplitudes
from typing import Dict, List, Callable, Optional
import matplotlib.pyplot as plt

from qwave.modules.quantum_waveform_generator import QuantumWaveformGenerator
from qwave.modules.audio_analyzer import AudioAnalyzer
from qwave.utils.quantum_audio_mapper import QuantumAudioMapper
from qwave.utils.constants import SAMPLING_RATE, DEFAULT_DURATION, DEFAULT_N_QUBITS


class QuantumOptimizer:
    """Music structure design using quantum optimization"""
    
    def __init__(
        self,
        n_qubits: int = DEFAULT_N_QUBITS,
        sampling_rate: int = SAMPLING_RATE,
        duration: float = DEFAULT_DURATION,
        cost_function: Optional[Callable] = None,
        ansatz: Optional[QuantumCircuit] = None
    ):
        """
        Args:
            n_qubits: Number of qubits
            sampling_rate: Sampling frequency
            duration: Audio duration
            cost_function: Custom cost function (uses default if None)
            ansatz: Custom ansatz circuit (uses default if None)
        """
        self.n_qubits = n_qubits
        self.sampling_rate = sampling_rate
        self.duration = duration
        
        self.generator = QuantumWaveformGenerator(
            n_qubits=n_qubits,
            sampling_rate=sampling_rate,
            duration=duration
        )
        self.analyzer = AudioAnalyzer(sampling_rate=sampling_rate)
        self.backend = Aer.get_backend('qasm_simulator')
        
        # Dependency injection
        self.custom_cost_function = cost_function
        self.custom_ansatz = ansatz
        
    def create_cost_function(
        self,
        target_emotion: str,
        target_genre: Optional[str] = None,
        target_features: Optional[Dict[str, float]] = None
    ) -> Callable:
        """
        Create a musical cost function
        
        Args:
            target_emotion: Target emotion ('energetic', 'calm', 'mysterious', 'happy')
            target_genre: Target genre (optional)
            target_features: Target features (optional)
            
        Returns:
            Cost function
        """
        if target_features is None:
            # Default features based on emotion
            emotion_features = {
                'energetic': {
                    'average_frequency': 0.8,
                    'spectral_centroid': 0.9,
                    'rhythmic_complexity': 0.8,
                    'harmonic_richness': 0.7
                },
                'calm': {
                    'average_frequency': 0.3,
                    'spectral_centroid': 0.3,
                    'rhythmic_complexity': 0.2,
                    'harmonic_richness': 0.5
                },
                'mysterious': {
                    'average_frequency': 0.5,
                    'spectral_centroid': 0.4,
                    'rhythmic_complexity': 0.6,
                    'harmonic_richness': 0.6
                },
                'happy': {
                    'average_frequency': 0.7,
                    'spectral_centroid': 0.7,
                    'rhythmic_complexity': 0.7,
                    'harmonic_richness': 0.8
                }
            }
            target_features = emotion_features.get(target_emotion, emotion_features['energetic'])
        
        def cost_function(circuit_params: np.ndarray) -> float:
            """Cost function"""
            try:
                # Generate circuit with parameters
                qc = self._create_parameterized_circuit(circuit_params)
                
                # Generate waveform
                waveform = self.generator.generate_waveform(
                    qc=qc,
                    shots=512,
                    apply_envelope=True,
                    apply_reverb=False
                )
                
                # Calculate features
                features = self.analyzer.analyze_audio_features(waveform)
                
                # Calculate cost (distance from target)
                cost = 0.0
                for feature_name, target_value in target_features.items():
                    actual_value = features.get(feature_name, 0.0)
                    cost += (actual_value - target_value) ** 2
                
                return cost
            except Exception as e:
                print(f"Error in cost function: {e}")
                return 1e10  # Large cost
        
        return cost_function
    
    def _create_parameterized_circuit(self, params: np.ndarray) -> QuantumCircuit:
        """
        Create parameterized circuit
        
        Args:
            params: Parameter array
            
        Returns:
            Quantum circuit
        """
        qc = QuantumCircuit(self.n_qubits)
        
        # Adjust number of parameters
        n_params = len(params)
        expected_params = 2 * self.n_qubits * 2  # ry + rz for 2 layers
        
        if n_params < expected_params:
            # Pad parameters
            params = np.pad(params, (0, expected_params - n_params), mode='reflect')
        elif n_params > expected_params:
            # Truncate parameters
            params = params[:expected_params]
        
        param_idx = 0
        
        # 2-layer parameterized gates
        for layer in range(2):
            # Ry gates
            for qubit in range(self.n_qubits):
                if param_idx < len(params):
                    qc.ry(params[param_idx], qubit)
                    param_idx += 1
            
            # Entanglement
            for i in range(self.n_qubits - 1):
                qc.cz(i, i+1)
            
            # Rz gates
            for qubit in range(self.n_qubits):
                if param_idx < len(params):
                    qc.rz(params[param_idx], qubit)
                    param_idx += 1
            
            # Entanglement
            if layer == 0:
                for i in range(0, self.n_qubits-1, 2):
                    qc.cz(i, i+1)
        
        qc.measure_all()
        
        return qc
    
    
    def optimize_parameters_heuristic(
        self,
        target_emotion: str,
        max_iterations: int = 50,
        optimizer: str = 'SPSA',
        progress_callback: Optional[Callable[[int, float], None]] = None
    ) -> tuple:
        """
        Optimize parameters using heuristic methods
        
        Args:
            target_emotion: Target emotion
            max_iterations: Maximum number of iterations
            optimizer: Optimization algorithm ('SPSA', 'COBYLA')
            progress_callback: Progress callback function (iteration, cost) -> None
            
        Returns:
            (optimal parameters, optimal cost)
        """
        # Create cost function
        if self.custom_cost_function:
            cost_function = self.custom_cost_function
        else:
            cost_function = self.create_cost_function(target_emotion)
        
        # Initial parameters
        n_params = 2 * self.n_qubits * 2
        initial_params = np.random.uniform(0, 2*np.pi, n_params)
        
        # Select optimizer
        if optimizer == 'SPSA':
            opt = SPSA(maxiter=max_iterations)
        elif optimizer == 'COBYLA':
            opt = COBYLA(maxiter=max_iterations)
        else:
            raise ValueError(f"Unknown optimizer: {optimizer}")
        
        # Execute optimization
        print(f"Optimizing for emotion: {target_emotion}")
        
        # Simple gradient descent (full VQE implementation requires quantum circuit evaluation)
        best_params = initial_params
        best_cost = cost_function(initial_params)
        
        for iteration in range(max_iterations):
            # Generate parameter candidates
            candidates = []
            for i in range(10):
                noise = np.random.normal(0, 0.1, len(best_params))
                candidate = (best_params + noise) % (2 * np.pi)
                candidates.append(candidate)
            
            # Select best candidate
            costs = [cost_function(c) for c in candidates]
            best_idx = np.argmin(costs)
            
            if costs[best_idx] < best_cost:
                best_params = candidates[best_idx]
                best_cost = costs[best_idx]
            
            # Call progress callback
            if progress_callback:
                progress_callback(iteration, best_cost)
            
            if iteration % 10 == 0:
                print(f"Iteration {iteration}: Cost = {best_cost:.4f}")
        
        print(f"Optimization completed. Final cost: {best_cost:.4f}")
        
        return best_params, best_cost
    
    def optimize_music_structure(
        self,
        target_emotion: str,
        output_file: Optional[str] = None,
        max_iterations: int = 50,
        progress_callback: Optional[Callable[[int, float], None]] = None
    ) -> np.ndarray:
        """
        Optimize music structure and generate waveform
        
        Args:
            target_emotion: Target emotion
            output_file: Output file path
            max_iterations: Maximum number of iterations
            progress_callback: Progress callback function (iteration, cost) -> None
            
        Returns:
            Optimized waveform
        """
        # Parameter optimization
        best_params, best_cost = self.optimize_parameters_heuristic(
            target_emotion=target_emotion,
            max_iterations=max_iterations,
            optimizer='SPSA',
            progress_callback=progress_callback
        )
        
        # Generate waveform with optimized circuit
        if self.custom_ansatz:
            qc = self.custom_ansatz
        else:
            qc = self._create_parameterized_circuit(best_params)
        waveform = self.generator.generate_waveform(
            qc=qc,
            shots=1024,
            apply_envelope=True,
            apply_reverb=True,
            output_file=output_file
        )
        
        # Display features
        features = self.analyzer.analyze_audio_features(waveform)
        print("\nGenerated audio features:")
        for name, value in features.items():
            print(f"  {name}: {value:.4f}")
        
        return waveform
    
    def explore_music_space(
        self,
        n_samples: int = 20,
        output_dir: str = "output_exploration"
    ) -> List[Dict]:
        """
        Explore music space and generate diverse samples
        
        Args:
            n_samples: Number of samples
            output_dir: Output directory
            
        Returns:
            List of generated sample information
        """
        import os
        os.makedirs(output_dir, exist_ok=True)
        
        samples = []
        emotions = ['energetic', 'calm', 'mysterious', 'happy']
        
        for i in range(n_samples):
            emotion = emotions[i % len(emotions)]
            
            # Random initial parameters
            n_params = 2 * self.n_qubits * 2
            params = np.random.uniform(0, 2*np.pi, n_params)
            
            # Create circuit
            qc = self._create_parameterized_circuit(params)
            
            # Generate waveform
            output_file = os.path.join(output_dir, f"sample_{i:03d}_{emotion}.wav")
            waveform = self.generator.generate_waveform(
                qc=qc,
                shots=512,
                apply_envelope=True,
                apply_reverb=True,
                output_file=output_file
            )
            
            # Calculate features
            features = self.analyzer.analyze_audio_features(waveform)
            
            samples.append({
                'index': i,
                'emotion': emotion,
                'file': output_file,
                'features': features
            })
            
            print(f"Generated sample {i+1}/{n_samples}: {emotion}")
        
        return samples
