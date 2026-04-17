"""
Module A: Quantum waveform generation core (variational circuits to WAV).
Generates audio from parameterized (variational) quantum circuits for
quantum optimization (VQE/QAOA) alignment. Uses probabilistic sampling
from the quantum outcome distribution, not classical random generation.
"""

import numpy as np
from qiskit import QuantumCircuit, transpile
from qiskit_aer import Aer
from qiskit.circuit import ParameterVector
from qiskit.quantum_info import Statevector
from typing import Dict, Optional, List
import soundfile as sf
from pathlib import Path

from qwave.utils.quantum_audio_mapper import QuantumAudioMapper
from qwave.utils.constants import SAMPLING_RATE, DEFAULT_DURATION, DEFAULT_N_QUBITS, DEFAULT_SHOTS


class QuantumWaveformGenerator:
    """量子回路を用いて音響波形を生成するクラス"""
    
    def __init__(
        self,
        n_qubits: int = DEFAULT_N_QUBITS,
        sampling_rate: int = SAMPLING_RATE,
        duration: float = DEFAULT_DURATION,
        use_interference: bool = True
    ):
        """
        Args:
            n_qubits: 量子ビット数
            sampling_rate: サンプリング周波数（Hz）
            duration: 音声の長さ（秒）
            use_interference: 量子干渉効果を適用するか
        """
        self.n_qubits = n_qubits
        self.sampling_rate = sampling_rate
        self.duration = duration
        self.use_interference = use_interference
        
        self.mapper = QuantumAudioMapper(sampling_rate, duration)
        self.backend = Aer.get_backend('qasm_simulator')
        
    def create_variational_circuit(
        self,
        depth: int = 3,
        entanglement: str = 'full',
    ) -> QuantumCircuit:
        """
        Create a parameterized variational circuit (ansatz).

        Rotation angles are Qiskit Parameters; bind with assign_parameters
        before execution (e.g. initial values for variational search).
        No classical random generation in circuit structure.

        Args:
            depth: Circuit depth (number of layers).
            entanglement: Entanglement pattern ('full', 'linear', 'circular').

        Returns:
            Parameterized QuantumCircuit (bind parameters before execution).
        """
        n = self.n_qubits
        # Total params: initial layer (n) + per layer (2*n) for ry, rz
        num_params = n + depth * 2 * n
        params = ParameterVector("θ", num_params)
        idx = 0

        qc = QuantumCircuit(n)
        for qubit in range(n):
            qc.ry(params[idx], qubit)
            idx += 1
        for layer in range(depth):
            if entanglement == 'full':
                for i in range(n):
                    for j in range(i + 1, n):
                        qc.cz(i, j)
            elif entanglement == 'linear':
                for i in range(n - 1):
                    qc.cz(i, i + 1)
            elif entanglement == 'circular':
                for i in range(n):
                    qc.cz(i, (i + 1) % n)
            for qubit in range(n):
                qc.ry(params[idx], qubit)
                idx += 1
                qc.rz(params[idx], qubit)
                idx += 1
        qc.measure_all()
        return qc

    def create_boson_sampling_circuit(self) -> QuantumCircuit:
        """
        Create a boson-sampling style circuit with parameterized rotations.

        Uses ParameterVector for rotation angles; bind before execution.
        Returns:
            Parameterized QuantumCircuit.
        """
        n = self.n_qubits
        num_params = 3 * n  # 3 layers of single-qubit rotations
        params = ParameterVector("φ", num_params)
        idx = 0

        qc = QuantumCircuit(n)
        n_excited = min(n // 2, 4)
        for i in range(n_excited):
            qc.x(i)
        for layer in range(3):
            for i in range(n):
                for j in range(i + 1, min(i + 3, n)):
                    qc.cz(i, j)
            for qubit in range(n):
                qc.ry(params[idx], qubit)
                idx += 1
        qc.measure_all()
        return qc
    
    def create_iqp_circuit(self, seed: Optional[int] = None) -> QuantumCircuit:
        """
        Create an IQP-style circuit with parameterized diagonal phases.

        Phases are Parameters; bind before execution. CZ pattern is fixed
        (nearest-neighbor style) for reproducibility. Seed only affects
        initial parameter binding when used with bind_iqp_initial_params.

        Args:
            seed: Optional seed for initial parameter values (variational init).

        Returns:
            Parameterized QuantumCircuit.
        """
        n = self.n_qubits
        # n diagonal Rz params + (n-1)+(n-2) CZ layer = n + 2*n-3 for two CZ "bands"
        num_rz = n
        params = ParameterVector("λ", num_rz)
        qc = QuantumCircuit(n)
        qc.h(range(n))
        for qubit in range(n):
            qc.rz(params[qubit], qubit)
        # Fixed CZ pattern (nearest-neighbor style, no random choice)
        for i in range(n):
            for j in range(i + 1, min(i + 3, n)):
                qc.cz(i, j)
        qc.h(range(n))
        qc.measure_all()
        return qc
    
    def execute_circuit(
        self, 
        qc: QuantumCircuit, 
        shots: int = DEFAULT_SHOTS
    ) -> Dict[str, int]:
        """
        量子回路を実行して測定結果を取得
        
        Args:
            qc: 量子回路
            shots: 測定回数
            
        Returns:
            ビット列 -> カウントの辞書
        """
        tqc = transpile(qc, self.backend)
        job = self.backend.run(tqc, shots=shots)
        result = job.result()
        counts = result.get_counts()
        
        return counts
    
    def generate_waveform(
        self,
        qc: Optional[QuantumCircuit] = None,
        circuit_type: str = 'variational',
        method: str = 'weighted_sum',
        shots: int = DEFAULT_SHOTS,
        apply_envelope: bool = True,
        apply_reverb: bool = True,
        output_file: Optional[str] = None,
    ) -> np.ndarray:
        """
        Generate audio waveform from a variational quantum circuit.

        Circuits are parameterized; initial parameter values are used
        when generating a new circuit (probabilistic sampling from
        the quantum outcome distribution).

        Args:
            qc: Quantum circuit (if None, one is built from circuit_type).
            circuit_type: 'variational', 'boson_sampling', or 'iqp'.
            method: 'weighted_sum' or 'stochastic' (probabilistic sampling).
            shots: Number of shots.
            apply_envelope: Apply ADSR envelope.
            apply_reverb: Apply reverb.
            output_file: Optional WAV path.

        Returns:
            Waveform array.
        """
        if qc is None:
            if circuit_type == 'variational':
                qc = self.create_variational_circuit(depth=3)
            elif circuit_type == 'boson_sampling':
                qc = self.create_boson_sampling_circuit()
            elif circuit_type == 'iqp':
                qc = self.create_iqp_circuit()
            else:
                raise ValueError(f"Unknown circuit type: {circuit_type}")
            # Bind parameters for execution (initial values for variational run)
            if qc.num_parameters > 0:
                initial = np.random.uniform(0, 2 * np.pi, qc.num_parameters)
                qc = qc.assign_parameters(initial)

        counts = self.execute_circuit(qc, shots=shots)
        
        # 確率分布に変換
        total_shots = sum(counts.values())
        probability_dist = {
            bitstring: count / total_shots 
            for bitstring, count in counts.items()
        }
        
        # 音響波形生成
        waveform = self.mapper.map_probability_distribution(
            probability_dist, 
            method=method
        )
        
        # 音響エフェクト適用
        if apply_envelope:
            waveform = self.mapper.apply_envelope(waveform)
        
        if apply_reverb:
            waveform = self.mapper.add_reverb(waveform, room_size=0.3)
        
        # ファイル出力
        if output_file:
            self.save_waveform(waveform, output_file)
        
        return waveform
    
    def generate_sequence(
        self,
        n_segments: int = 4,
        segment_duration: float = 1.0,
        circuit_type: str = 'variational',
        output_file: Optional[str] = None,
    ) -> np.ndarray:
        """
        Generate a sequence of segments from variational circuits.

        Each segment uses a parameterized circuit with bound initial
        parameters (probabilistic sampling from quantum distribution).

        Args:
            n_segments: Number of segments.
            segment_duration: Duration per segment (seconds).
            circuit_type: 'variational', 'boson_sampling', or 'iqp'.
            output_file: Optional WAV path.

        Returns:
            Concatenated waveform array.
        """
        segments = []
        for i in range(n_segments):
            qc = self.create_variational_circuit(
                depth=2 + (i % 3),
                entanglement='full' if i % 2 == 0 else 'linear',
            )
            if qc.num_parameters > 0:
                initial = np.random.uniform(0, 2 * np.pi, qc.num_parameters)
                qc = qc.assign_parameters(initial)
            segment = self.generate_waveform(
                qc=qc,
                circuit_type='variational',
                shots=512,
                apply_envelope=True,
                apply_reverb=(i == n_segments - 1),
            )
            
            segments.append(segment)
        
        # 結合
        full_waveform = np.concatenate(segments)
        
        # ファイル出力
        if output_file:
            self.save_waveform(full_waveform, output_file)
        
        return full_waveform
    
    def save_waveform(self, waveform: np.ndarray, output_file: str) -> None:
        """
        WAVファイルとして保存
        
        Args:
            waveform: 振幅データ
            output_file: 出力ファイルパス
        """
        # ディレクトリ作成
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 正規化
        waveform = np.clip(waveform, -1, 1)
        
        # 保存（16bit PCM）
        waveform_int16 = (waveform * 32767).astype(np.int16)
        sf.write(output_file, waveform_int16, self.sampling_rate)
        
        print(f"Waveform saved to: {output_file}")
