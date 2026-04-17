#!/usr/bin/env python3
"""
Q-Wave Main GUI Application

A unified graphical user interface for building quantum circuits and generating
non-classical audio patterns. Combines visual circuit building with quantum
optimization and analysis capabilities.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
import os
import tempfile
import pygame
import numpy as np
import soundfile as sf
from datetime import datetime
from pathlib import Path
from qiskit.qasm2 import dumps
import time

from qwave.gui.circuit_builder import CircuitBuilderWidget
from qwave.gui.visualization import WaveformPlotter, MultiPanelVisualizer
from qwave.modules.simulator import QuantumSimulator
from qwave.modules.generator import AudioGenerator
from qwave.modules.analyzer import SpectralAnalyzer
from qwave.modules.optimizer import QuantumOptimizer
from qwave.scripts.verify_quantum_walk import build_quantum_walk_circuit
from qwave.utils.constants import (
    SAMPLING_RATE, DEFAULT_DURATION, DEFAULT_SHOTS, DEFAULT_N_QUBITS,
    DEFAULT_WINDOW_WIDTH, DEFAULT_WINDOW_HEIGHT, DEFAULT_CIRCUIT_BUILDER_QUBITS,
    DEFAULT_OUTPUT_DIR, DEFAULT_GENERATED_AUDIO_DIR
)


class QWaveGUI:
    """
    Main GUI application for Q-Wave quantum audio generation.
    """
    
    def __init__(self, root):
        """Initialize the GUI application."""
        self.root = root
        self.root.title("Q-Wave: Quantum Circuit Audio Generator")
        self.root.geometry(f"{DEFAULT_WINDOW_WIDTH}x{DEFAULT_WINDOW_HEIGHT}")
        
        # Initialize pygame for audio playback
        pygame.mixer.init()
        
        # Current audio file path
        self.current_audio_path = None
        self.latest_waveform = None
        self.latest_sample_rate = None
        self.is_generating = False
        
        # Output directory
        self.output_dir = Path(DEFAULT_GENERATED_AUDIO_DIR)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.waveform_image_dir = self.output_dir.parent / "generated_waveform"
        self.waveform_image_dir.mkdir(parents=True, exist_ok=True)
        
        # Waveform window for playback monitoring
        self.waveform_window = None
        self.waveform_window_canvas = None
        self.waveform_progress_line = None
        self.playback_monitor_id = None
        self.current_waveform_duration = None
        self.playback_start_time = None
        
        # Initialize modules
        self.simulator = QuantumSimulator(shots=DEFAULT_SHOTS)
        self.generator = AudioGenerator(sample_rate=SAMPLING_RATE)
        self.analyzer = SpectralAnalyzer(sample_rate=SAMPLING_RATE)
        self.optimizer = QuantumOptimizer(
            n_qubits=DEFAULT_N_QUBITS,
            sampling_rate=SAMPLING_RATE,
            duration=DEFAULT_DURATION
        )
        
        # Create UI
        self.create_widgets()
        
    def create_widgets(self):
        """Create and layout all GUI widgets."""
        # Main container
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(0, weight=1)

        # Single-screen layout: use the former Circuit Builder tab as the unified UI.
        self.create_circuit_builder_tab(main_frame)
        
        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN)
        status_bar.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(5, 0))
    
    def create_circuit_builder_tab(self, parent):
        """Create the unified main screen (formerly the Circuit Builder tab)."""
        tab_frame = ttk.Frame(parent, padding="10")
        tab_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        tab_frame.columnconfigure(1, weight=1)
        tab_frame.columnconfigure(2, weight=1)
        tab_frame.rowconfigure(0, weight=1)
        tab_frame.rowconfigure(1, weight=1)
        
        # Left panel: Gate selection and controls
        left_panel = ttk.Frame(tab_frame)
        left_panel.grid(row=0, column=0, rowspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 10))
        
        # Gate selection panel
        gate_frame = ttk.LabelFrame(left_panel, text="Quantum Gates", padding="10")
        gate_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.selected_gate = tk.StringVar()
        gate_buttons = [
            ('H', 'H (Hadamard)'),
            ('X', 'X (Pauli-X)'),
            ('Y', 'Y (Pauli-Y)'),
            ('Z', 'Z (Pauli-Z)'),
            ('T', 'T (Phase)'),
            ('S', 'S (Phase)'),
            ('CNOT', 'CNOT (Entanglement)'),
            ('CZ', 'CZ (Controlled-Z)'),
            ('M', 'M (Measurement)'),
        ]
        
        for gate_type, label in gate_buttons:
            btn = ttk.Radiobutton(
                gate_frame,
                text=label,
                variable=self.selected_gate,
                value=gate_type,
                command=self.on_gate_selected
            )
            btn.pack(anchor=tk.W, pady=2)
        
        # Clear button
        ttk.Button(gate_frame, text="Clear Circuit", 
                  command=self.clear_circuit).pack(fill=tk.X, pady=(10, 0))
        
        # Circuit parameters
        params_frame = ttk.LabelFrame(left_panel, text="Circuit Parameters", padding="10")
        params_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Number of qubits
        ttk.Label(params_frame, text="Number of Qubits:").pack(anchor=tk.W)
        self.num_qubits_var = tk.IntVar(value=DEFAULT_CIRCUIT_BUILDER_QUBITS)
        qubits_spin = ttk.Spinbox(params_frame, from_=2, to=10, 
                                  textvariable=self.num_qubits_var,
                                  command=self.update_num_qubits, width=10)
        qubits_spin.pack(anchor=tk.W, pady=(0, 10))
        
        # Audio generation parameters
        audio_frame = ttk.LabelFrame(left_panel, text="Audio Parameters", padding="10")
        audio_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Duration
        ttk.Label(audio_frame, text="Duration (seconds):").pack(anchor=tk.W)
        self.duration_var = tk.DoubleVar(value=DEFAULT_DURATION)
        duration_spin = ttk.Spinbox(audio_frame, from_=0.5, to=60.0, increment=0.5,
                                   textvariable=self.duration_var, width=10)
        duration_spin.pack(anchor=tk.W, pady=(0, 5))
        
        # Sample rate
        ttk.Label(audio_frame, text="Sample Rate (Hz):").pack(anchor=tk.W)
        self.sample_rate_var = tk.IntVar(value=SAMPLING_RATE)
        sample_rate_combo = ttk.Combobox(audio_frame, textvariable=self.sample_rate_var,
                                        values=[22050, 44100, 48000, 96000], width=10, state='readonly')
        sample_rate_combo.pack(anchor=tk.W, pady=(0, 5))
        
        # Shots
        ttk.Label(audio_frame, text="Measurement Shots:").pack(anchor=tk.W)
        self.shots_var = tk.IntVar(value=DEFAULT_SHOTS)
        shots_spin = ttk.Spinbox(audio_frame, from_=128, to=8192, increment=128,
                               textvariable=self.shots_var, width=10)
        shots_spin.pack(anchor=tk.W, pady=(0, 10))
        
        # Control buttons
        control_frame = ttk.Frame(left_panel)
        control_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Button(control_frame, text="Generate Audio", 
                  command=self.generate_audio).pack(fill=tk.X, pady=(0, 5))
        ttk.Button(control_frame, text="Play Audio", 
                  command=self.play_audio).pack(fill=tk.X, pady=(0, 5))
        ttk.Button(control_frame, text="Stop Audio", 
                  command=self.stop_audio).pack(fill=tk.X, pady=(0, 5))
        ttk.Button(control_frame, text="Save Audio", 
                  command=self.save_audio).pack(fill=tk.X, pady=(0, 5))
        ttk.Button(control_frame, text="Load Circuit", 
                  command=self.load_circuit).pack(fill=tk.X, pady=(0, 5))
        ttk.Button(control_frame, text="Save Circuit", 
                  command=self.save_circuit).pack(fill=tk.X)
        
        # Left top: Quantum circuit
        center_frame = ttk.Frame(tab_frame)
        center_frame.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 10))
        center_frame.columnconfigure(0, weight=1)
        center_frame.rowconfigure(0, weight=1)
        
        circuit_label = ttk.Label(center_frame, text="Quantum Circuit Builder")
        circuit_label.pack(anchor=tk.W, pady=(0, 5))
        
        # Create scrollable canvas for circuit builder
        canvas_frame = ttk.Frame(center_frame)
        canvas_frame.pack(fill=tk.BOTH, expand=True)
        
        scrollbar_v = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL)
        scrollbar_h = ttk.Scrollbar(canvas_frame, orient=tk.HORIZONTAL)
        
        self.circuit_builder = CircuitBuilderWidget(
            canvas_frame,
            num_qubits=self.num_qubits_var.get(),
            width=600,
            height=400,
            bg='white'
        )
        
        scrollbar_v.config(command=self.circuit_builder.yview)
        scrollbar_h.config(command=self.circuit_builder.xview)
        self.circuit_builder.config(yscrollcommand=scrollbar_v.set,
                                   xscrollcommand=scrollbar_h.set)
        
        scrollbar_v.pack(side=tk.RIGHT, fill=tk.Y)
        scrollbar_h.pack(side=tk.BOTTOM, fill=tk.X)
        self.circuit_builder.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Left bottom: generated waveform
        waveform_frame = ttk.LabelFrame(tab_frame, text="Waveform", padding="5")
        waveform_frame.grid(
            row=1, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 10), pady=(10, 0)
        )
        self.waveform_plotter = WaveformPlotter(waveform_frame)
        self.waveform_plotter.get_widget().pack(fill=tk.BOTH, expand=True)
        self.waveform_plotter.clear()
        
        # Right top: spectral metrics
        metrics_frame = ttk.LabelFrame(tab_frame, text="Spectral Analysis Metrics", padding="5")
        metrics_frame.grid(row=0, column=2, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.analysis_text = scrolledtext.ScrolledText(
            metrics_frame, width=40, height=14, wrap=tk.WORD
        )
        self.analysis_text.pack(fill=tk.BOTH, expand=True)
        
        # Right bottom: log output
        log_frame = ttk.LabelFrame(tab_frame, text="Log", padding="5")
        log_frame.grid(row=1, column=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(10, 0))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=8, wrap=tk.WORD)
        self.log_text.pack(fill=tk.BOTH, expand=True)
    
    def create_waveform_generation_tab(self):
        """Create Waveform Generation tab."""
        tab_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(tab_frame, text="Waveform Generation")
        
        tab_frame.columnconfigure(1, weight=1)
        tab_frame.rowconfigure(0, weight=1)
        
        # Left panel: Controls
        control_frame = ttk.LabelFrame(tab_frame, text="Generation Parameters", padding="10")
        control_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 10))
        
        # Number of qubits
        ttk.Label(control_frame, text="Number of Qubits:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.gen_n_qubits_var = tk.IntVar(value=DEFAULT_N_QUBITS)
        ttk.Spinbox(control_frame, from_=4, to=12, textvariable=self.gen_n_qubits_var, width=10).grid(
            row=0, column=1, sticky=tk.W, padx=5, pady=5
        )
        
        # Circuit type
        ttk.Label(control_frame, text="Circuit Type:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.circuit_type_var = tk.StringVar(value="custom")
        circuit_combo = ttk.Combobox(
            control_frame,
            textvariable=self.circuit_type_var,
            values=["custom", "variational", "iqp", "quantum_walk"],
            state="readonly",
            width=15
        )
        circuit_combo.grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Duration
        ttk.Label(control_frame, text="Duration (s):").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.gen_duration_var = tk.DoubleVar(value=DEFAULT_DURATION)
        ttk.Spinbox(control_frame, from_=0.5, to=60.0, increment=0.5,
                   textvariable=self.gen_duration_var, width=10).grid(
            row=2, column=1, sticky=tk.W, padx=5, pady=5
        )
        
        # Shots
        ttk.Label(control_frame, text="Shots:").grid(row=3, column=0, sticky=tk.W, pady=5)
        self.gen_shots_var = tk.IntVar(value=DEFAULT_SHOTS)
        ttk.Spinbox(control_frame, from_=256, to=8192, increment=256,
                   textvariable=self.gen_shots_var, width=10).grid(
            row=3, column=1, sticky=tk.W, padx=5, pady=5
        )
        
        # Effects
        effects_frame = ttk.LabelFrame(control_frame, text="Audio Effects", padding="5")
        effects_frame.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=10)
        
        self.apply_envelope_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(effects_frame, text="Apply ADSR Envelope",
                       variable=self.apply_envelope_var).pack(anchor=tk.W)
        
        self.apply_reverb_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(effects_frame, text="Apply Reverb",
                       variable=self.apply_reverb_var).pack(anchor=tk.W)
        
        # Generate button
        ttk.Button(control_frame, text="Generate Quantum Waveform",
                  command=self.generate_waveform_tab).grid(
            row=5, column=0, columnspan=2, pady=20, sticky=(tk.W, tk.E)
        )
        
        # Save button
        ttk.Button(control_frame, text="Save Current Waveform",
                  command=self.save_waveform_tab).grid(
            row=6, column=0, columnspan=2, pady=5, sticky=(tk.W, tk.E)
        )
        
        # Right panel: Visualization
        vis_frame = ttk.LabelFrame(tab_frame, text="Visualization", padding="10")
        vis_frame.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S))
        vis_frame.columnconfigure(0, weight=1)
        vis_frame.rowconfigure(0, weight=1)
        
        self.gen_visualizer = MultiPanelVisualizer(vis_frame, nrows=2, ncols=2)
        self.gen_visualizer.get_widget().pack(fill=tk.BOTH, expand=True)
        self.gen_visualizer.clear()
    
    def create_optimization_tab(self):
        """Create Optimization tab."""
        tab_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(tab_frame, text="Optimization")
        
        tab_frame.columnconfigure(1, weight=1)
        tab_frame.rowconfigure(0, weight=1)
        
        # Left panel: Controls
        control_frame = ttk.LabelFrame(tab_frame, text="Optimization Parameters", padding="10")
        control_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 10))
        
        # Target emotion
        ttk.Label(control_frame, text="Target Emotion:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.emotion_var = tk.StringVar(value="energetic")
        emotion_combo = ttk.Combobox(
            control_frame,
            textvariable=self.emotion_var,
            values=["energetic", "calm", "mysterious", "happy"],
            state="readonly",
            width=15
        )
        emotion_combo.grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Max iterations
        ttk.Label(control_frame, text="Max Iterations:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.max_iter_var = tk.IntVar(value=20)
        ttk.Spinbox(control_frame, from_=10, to=100, increment=10,
                   textvariable=self.max_iter_var, width=10).grid(
            row=1, column=1, sticky=tk.W, padx=5, pady=5
        )
        
        # Optimization button
        ttk.Button(control_frame, text="Optimize Music Structure",
                  command=self.optimize_music).grid(
            row=2, column=0, columnspan=2, pady=20, sticky=(tk.W, tk.E)
        )
        
        # Progress display
        self.progress_var = tk.StringVar(value="")
        progress_label = ttk.Label(control_frame, textvariable=self.progress_var)
        progress_label.grid(row=3, column=0, columnspan=2, pady=5)
        
        # Right panel: Visualization
        vis_frame = ttk.LabelFrame(tab_frame, text="Optimized Waveform", padding="10")
        vis_frame.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S))
        vis_frame.columnconfigure(0, weight=1)
        vis_frame.rowconfigure(0, weight=1)
        
        self.opt_visualizer = MultiPanelVisualizer(vis_frame, nrows=2, ncols=2)
        self.opt_visualizer.get_widget().pack(fill=tk.BOTH, expand=True)
        self.opt_visualizer.clear()
    
    def create_analysis_tab(self):
        """Create Analysis tab."""
        tab_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(tab_frame, text="Analysis")
        
        tab_frame.columnconfigure(1, weight=1)
        tab_frame.rowconfigure(0, weight=1)
        
        # Left panel: Controls
        control_frame = ttk.LabelFrame(tab_frame, text="Analysis Controls", padding="10")
        control_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 10))
        
        # Audio file selection
        ttk.Label(control_frame, text="Audio File:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.audio_file_var = tk.StringVar(value="")
        ttk.Entry(control_frame, textvariable=self.audio_file_var, width=30).grid(
            row=0, column=1, sticky=(tk.W, tk.E), padx=5, pady=5
        )
        ttk.Button(control_frame, text="Browse...", command=self.browse_audio_file).grid(
            row=0, column=2, padx=5, pady=5
        )
        
        # Analysis button
        ttk.Button(control_frame, text="Analyze Audio",
                  command=self.analyze_audio).grid(
            row=1, column=0, columnspan=3, pady=20, sticky=(tk.W, tk.E)
        )
        
        # Results display area
        ttk.Label(control_frame, text="Analysis Results:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.results_text = tk.Text(control_frame, height=15, width=40)
        self.results_text.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E), padx=5, pady=5)
        
        # Right panel: Visualization
        vis_frame = ttk.LabelFrame(tab_frame, text="Analysis Visualization", padding="10")
        vis_frame.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S))
        vis_frame.columnconfigure(0, weight=1)
        vis_frame.rowconfigure(0, weight=1)
        
        self.analysis_visualizer = MultiPanelVisualizer(vis_frame, nrows=2, ncols=2)
        self.analysis_visualizer.get_widget().pack(fill=tk.BOTH, expand=True)
        self.analysis_visualizer.clear()
    
    # Event handlers
    def on_gate_selected(self):
        """Handle gate selection."""
        gate_type = self.selected_gate.get()
        self.circuit_builder.set_selected_gate(gate_type)
        self.log(f"Selected gate: {gate_type}")
    
    def update_num_qubits(self):
        """Update the number of qubits in the circuit."""
        num_qubits = self.num_qubits_var.get()
        # Note: Full implementation would require recreating the widget
        self.log(f"Number of qubits changed to {num_qubits}")
    
    def clear_circuit(self):
        """Clear the quantum circuit."""
        self.circuit_builder.clear_circuit()
        self.log("Circuit cleared")
    
    def generate_audio(self):
        """Generate audio from the quantum circuit in a separate thread."""
        if self.is_generating:
            messagebox.showinfo("Busy", "Audio generation is already in progress.")
            return
        self.is_generating = True
        
        def generate():
            try:
                self.root.after(0, self.set_status, "Generating audio...")
                
                # Get parameters
                duration = self.duration_var.get()
                sample_rate = self.sample_rate_var.get()
                shots = self.shots_var.get()
                
                # Convert circuit to Qiskit
                circuit = self.circuit_builder.to_qiskit_circuit()
                
                if circuit.size() == 0:
                    self.root.after(0, messagebox.showwarning, 
                                  "Empty Circuit", "Please add gates to the circuit first.")
                    return
                
                # Run simulation
                self.root.after(0, self.log, "Running quantum simulation...")
                self.simulator.shots = shots
                self.simulator.load_circuit(circuit)
                statevector = self.simulator.get_statevector()
                measurement_sequence = self.simulator.get_measurement_sequence()
                probability_dist = self.simulator.get_probability_distribution()
                
                self.root.after(0, self.log, f"Simulation completed: {len(measurement_sequence)} outcomes")
                
                # Generate audio
                self.root.after(0, self.log, "Generating audio waveform...")
                self.generator.sample_rate = sample_rate
                waveform = self.generator.map_quantum_to_audio(
                    statevector=statevector,
                    measurement_sequence=measurement_sequence,
                    probability_distribution=probability_dist,
                    duration=duration,
                    apply_envelope=True,
                    apply_reverb=False
                )
                
                # Save to output directory
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = self.output_dir / f"qwave_{timestamp}.wav"
                waveform_png = self.waveform_image_dir / f"qwave_{timestamp}.png"
                self.generator.save_wav(waveform, str(filename))
                self.current_audio_path = str(filename)
                self.latest_waveform = waveform
                self.latest_sample_rate = sample_rate
                
                # Perform analysis
                self.root.after(0, self.log, "Performing spectral analysis...")
                analysis_results = self.analyzer.analyze(
                    waveform, prob_dist=probability_dist
                )
                
                # Display analysis
                self.root.after(0, self.display_analysis, analysis_results)
                
                # Update visualization and save the left-bottom waveform panel as PNG.
                self.root.after(
                    0,
                    self.plot_and_save_waveform_panel,
                    waveform,
                    sample_rate,
                    str(waveform_png),
                )
                
                self.root.after(0, self.set_status, "Audio generated successfully!")
                self.root.after(0, self.log, f"Audio saved to: {filename}")
                self.root.after(0, self.log, f"Waveform PNG saved to: {waveform_png}")
                
            except Exception as e:
                self.root.after(0, messagebox.showerror, "Error", f"Failed to generate audio: {str(e)}")
                self.root.after(0, self.log, f"Error: {str(e)}")
            finally:
                def finish():
                    self.is_generating = False
                self.root.after(0, finish)
        
        thread = threading.Thread(target=generate, daemon=True)
        thread.start()
    
    def generate_waveform_tab(self):
        """Generate waveform from Waveform Generation tab."""
        if self.is_generating:
            messagebox.showinfo("Busy", "Audio generation is already in progress.")
            return
        self.is_generating = True
        
        def generate():
            try:
                self.root.after(0, self.set_status, "Generating quantum waveform...")
                
                # Get parameters
                n_qubits = self.gen_n_qubits_var.get()
                duration = self.gen_duration_var.get()
                shots = self.gen_shots_var.get()
                circuit_type = self.circuit_type_var.get()
                
                from qiskit import QuantumCircuit
                if circuit_type == "quantum_walk":
                    circuit = build_quantum_walk_circuit(
                        steps=n_qubits, num_qubits=n_qubits - 1
                    )
                    interference_mode = True
                else:
                    # Placeholder for custom / variational / iqp
                    circuit = QuantumCircuit(n_qubits)
                    circuit.h(range(n_qubits))
                    circuit.measure_all()
                    interference_mode = False
                
                # Simulate
                self.simulator.shots = shots
                self.simulator.load_circuit(circuit)
                statevector = self.simulator.get_statevector()
                measurement_sequence = self.simulator.get_measurement_sequence()
                probability_dist = self.simulator.get_probability_distribution()
                
                # Generate audio
                self.generator.sample_rate = SAMPLING_RATE
                waveform = self.generator.map_quantum_to_audio(
                    statevector=statevector,
                    measurement_sequence=measurement_sequence,
                    probability_distribution=probability_dist,
                    duration=duration,
                    apply_envelope=self.apply_envelope_var.get(),
                    apply_reverb=self.apply_reverb_var.get(),
                    interference_mode=interference_mode,
                )
                
                self.latest_waveform = waveform
                self.latest_sample_rate = SAMPLING_RATE
                
                # Visualize
                self.root.after(0, self.gen_visualizer.plot_waveform, waveform, SAMPLING_RATE, 0)
                self.root.after(0, self.gen_visualizer.plot_spectrum, waveform, SAMPLING_RATE, 1)
                self.root.after(0, self.gen_visualizer.plot_spectrogram, waveform, SAMPLING_RATE, 2)
                
                # Analyze features
                features = self.analyzer.analyze(
                    waveform, prob_dist=probability_dist
                )
                self.root.after(0, self.gen_visualizer.plot_features, features, 3)
                
                self.root.after(0, self.set_status, "Waveform generated successfully")
                
            except Exception as e:
                self.root.after(0, messagebox.showerror, "Error", f"Failed to generate waveform: {str(e)}")
            finally:
                def finish():
                    self.is_generating = False
                self.root.after(0, finish)
        
        thread = threading.Thread(target=generate, daemon=True)
        thread.start()
    
    def optimize_music(self):
        """Optimize music structure."""
        if self.is_generating:
            messagebox.showinfo("Busy", "Optimization is already in progress.")
            return
        self.is_generating = True
        
        def optimize():
            try:
                emotion = self.emotion_var.get()
                max_iter = self.max_iter_var.get()
                
                def progress_callback(iteration, cost):
                    progress = f"Optimizing... {iteration}/{max_iter} (Cost: {cost:.4f})"
                    self.root.after(0, lambda p=progress: self.progress_var.set(p))
                
                self.root.after(0, self.set_status, "Optimizing music structure...")
                
                waveform = self.optimizer.optimize_music_structure(
                    target_emotion=emotion,
                    max_iterations=max_iter,
                    progress_callback=progress_callback
                )
                
                self.latest_waveform = waveform
                self.latest_sample_rate = SAMPLING_RATE
                
                # Visualize
                self.root.after(0, self.opt_visualizer.plot_waveform, waveform, SAMPLING_RATE, 0)
                self.root.after(0, self.opt_visualizer.plot_spectrum, waveform, SAMPLING_RATE, 1)
                self.root.after(0, self.opt_visualizer.plot_spectrogram, waveform, SAMPLING_RATE, 2)
                
                features = self.analyzer.analyze_audio_features(waveform)
                self.root.after(0, self.opt_visualizer.plot_features, features, 3)
                
                self.root.after(0, self.set_status, "Optimization completed")
                self.root.after(0, lambda: self.progress_var.set(""))
                
            except Exception as e:
                self.root.after(0, messagebox.showerror, "Error", f"Optimization failed: {str(e)}")
            finally:
                def finish():
                    self.is_generating = False
                self.root.after(0, finish)
        
        thread = threading.Thread(target=optimize, daemon=True)
        thread.start()
    
    def analyze_audio(self):
        """Analyze audio file."""
        filename = self.audio_file_var.get()
        if not filename or not os.path.exists(filename):
            messagebox.showerror("Error", "Please select a valid audio file.")
            return
        
        try:
            waveform, sr = self.analyzer.load_audio(filename)
            features = self.analyzer.analyze(waveform)
            
            # Display results
            self.results_text.delete(1.0, tk.END)
            for key, value in features.items():
                self.results_text.insert(tk.END, f"{key}: {value:.4f}\n")
            
            # Visualize
            self.analysis_visualizer.plot_waveform(waveform, sr, 0)
            self.analysis_visualizer.plot_spectrum(waveform, sr, 1)
            self.analysis_visualizer.plot_spectrogram(waveform, sr, 2)
            self.analysis_visualizer.plot_features(features, 3)
            
            self.set_status("Analysis completed")
            
        except Exception as e:
            messagebox.showerror("Error", f"Analysis failed: {str(e)}")
    
    def browse_audio_file(self):
        """Select audio file."""
        filename = filedialog.askopenfilename(
            filetypes=[("Audio files", "*.wav *.mp3 *.flac"), ("All files", "*.*")]
        )
        if filename:
            self.audio_file_var.set(filename)
    
    def play_audio(self):
        """Play the generated audio."""
        if self.current_audio_path is None and self.latest_waveform is None:
            messagebox.showwarning("No Audio", "Please generate audio first.")
            return
        
        waveform = self.latest_waveform
        sample_rate = self.latest_sample_rate
        
        if waveform is None and self.current_audio_path:
            try:
                waveform, sample_rate = sf.read(self.current_audio_path)
                self.latest_waveform = waveform
                self.latest_sample_rate = sample_rate
            except Exception as exc:
                messagebox.showerror("Error", f"Failed to load audio for playback: {exc}")
                return
        
        if waveform is None:
            return
        
        try:
            # Save temporary file for playback
            temp_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
            temp_path = temp_file.name
            temp_file.close()
            
            if waveform.ndim > 1:
                waveform = np.mean(waveform, axis=1)
            
            sf.write(temp_path, waveform, int(sample_rate))
            
            target_rate = int(sample_rate) if sample_rate else SAMPLING_RATE
            if pygame.mixer.get_init():
                pygame.mixer.quit()
            pygame.mixer.init(frequency=target_rate)
            pygame.mixer.music.load(temp_path)
            pygame.mixer.music.set_volume(1.0)
            pygame.mixer.music.play()
            
            # Keep playback visualization in the left-bottom waveform panel.
            self.waveform_plotter.plot_waveform(waveform, int(sample_rate))
            self.waveform_plotter.set_playback_cursor(0.0)
            self.log("Playing audio...")
            self.set_status("Playing audio...")
            
            self.start_waveform_monitor()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to play audio: {str(e)}")
    
    def stop_audio(self):
        """Stop audio playback."""
        if pygame.mixer.get_init():
            pygame.mixer.music.stop()
        self.stop_waveform_monitor()
        self.waveform_plotter.set_playback_cursor(self.waveform_plotter.waveform_duration)
        self.log("Audio stopped")
        self.set_status("Ready")
    
    def save_audio(self):
        """Save the generated audio to a file."""
        if self.current_audio_path is None:
            messagebox.showwarning("No Audio", "Please generate audio first.")
            return
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".wav",
            filetypes=[("WAV files", "*.wav"), ("All files", "*.*")]
        )
        
        if filename:
            try:
                import shutil
                shutil.copy(self.current_audio_path, filename)
                self.log(f"Audio saved to: {filename}")
                messagebox.showinfo("Success", f"Audio saved to:\n{filename}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save audio: {str(e)}")
    
    def save_waveform_tab(self):
        """Save waveform from Waveform Generation tab."""
        if self.latest_waveform is None:
            messagebox.showwarning("No Waveform", "Please generate a waveform first.")
            return
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".wav",
            filetypes=[("WAV files", "*.wav")],
            initialdir=self.output_dir
        )
        
        if filename:
            self.generator.save_wav(self.latest_waveform, filename)
            messagebox.showinfo("Success", f"Waveform saved to: {filename}")
    
    def load_circuit(self):
        """Load a quantum circuit from a QASM file."""
        filename = filedialog.askopenfilename(
            filetypes=[("QASM files", "*.qasm"), ("All files", "*.*")]
        )
        
        if filename:
            try:
                circuit = self.simulator.load_circuit_from_qasm(filename)
                
                # Update number of qubits if needed
                if circuit.num_qubits != self.num_qubits_var.get():
                    self.num_qubits_var.set(circuit.num_qubits)

                self.circuit_builder.load_from_qiskit_circuit(circuit)

                self.log(f"Circuit loaded from: {filename}")
                self.log("Visual reconstruction complete.")
                messagebox.showinfo(
                    "Success",
                    f"Circuit successfully loaded and reconstructed from:\n{filename}",
                )
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load circuit: {str(e)}")
    
    def save_circuit(self):
        """Save the current circuit to a QASM file."""
        filename = filedialog.asksaveasfilename(
            defaultextension=".qasm",
            filetypes=[("QASM files", "*.qasm"), ("All files", "*.*")]
        )
        
        if filename:
            try:
                self.circuit_builder.save_to_qasm(filename)
                self.log(f"Circuit saved to: {filename}")
                messagebox.showinfo("Success", f"Circuit saved to:\n{filename}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save circuit: {str(e)}")
    
    def display_analysis(self, results: dict):
        """Display spectral analysis results."""
        self.analysis_text.delete(1.0, tk.END)
        
        text = "=" * 50 + "\n"
        text += "QUANTUM AUDIO SPECTRAL ANALYSIS\n"
        text += "=" * 50 + "\n\n"
        
        text += "--- Basic Spectral Features ---\n"
        text += f"Spectral Centroid:      {results.get('spectral_centroid_hz', 0):.2f} Hz\n"
        text += f"Spectral Bandwidth:     {results.get('spectral_bandwidth_hz', 0):.2f} Hz\n"
        text += f"Spectral Rolloff:       {results.get('spectral_rolloff_hz', 0):.2f} Hz\n"
        text += "\n"
        
        text += "--- Non-Stationarity Analysis ---\n"
        text += f"Non-Stationarity Index: {results.get('non_stationarity_index', 0):.4f}\n"
        text += f"Temporal Variation:     {results.get('temporal_variation', 0):.4f}\n\n"
        
        text += "--- Modulation Characteristics ---\n"
        text += f"Modulation Depth:              {results.get('modulation_depth', 0):.4f}\n"
        text += f"Frequency Modulation Index:    {results.get('frequency_modulation_index', 0):.4f}\n"
        text += f"Avg Spectral Spread:           {results.get('average_spectral_spread_hz', 0):.2f} Hz\n"
        text += f"Spectral Spread Variation:     {results.get('spectral_spread_variation', 0):.4f}\n\n"
        
        text += "--- Quantum Pattern Indicators ---\n"
        text += f"Spectral Entropy:       {results.get('spectral_entropy', 0):.4f}\n"
        
        self.analysis_text.insert(1.0, text)

    def plot_and_save_waveform_panel(self, waveform: np.ndarray, sample_rate: int, png_path: str):
        """Render waveform panel and save the panel figure as PNG."""
        self.waveform_plotter.plot_waveform(waveform, sample_rate)
        self.waveform_plotter.figure.savefig(png_path, dpi=150, bbox_inches="tight")
    
    def open_waveform_window(self, waveform: np.ndarray, sample_rate: int):
        """Open a separate window displaying the waveform."""
        if waveform is None or sample_rate is None:
            return
        if waveform.ndim > 1:
            waveform = np.mean(waveform, axis=1)
        
        duration = len(waveform) / sample_rate
        time_axis = np.linspace(0, duration, len(waveform))
        max_points = 10000
        if len(waveform) > max_points:
            indices = np.linspace(0, len(waveform) - 1, max_points).astype(int)
            waveform = waveform[indices]
            time_axis = time_axis[indices]

        self.close_waveform_window()
        window = tk.Toplevel(self.root)
        window.title("Waveform Viewer")
        window.geometry("800x320")

        from matplotlib.figure import Figure
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        
        fig = Figure(figsize=(8, 3), dpi=100)
        ax_wave = fig.add_subplot(211)
        ax_spec = fig.add_subplot(212)
        ax_wave.plot(time_axis, waveform, linewidth=0.8)
        ax_wave.set_title("Audio Waveform")
        ax_wave.set_xlabel("Time (s)")
        ax_wave.set_ylabel("Amplitude")
        ax_wave.margins(x=0)
        progress_line = ax_wave.axvline(0, color='red', linewidth=1, label='Playback Position')
        
        import librosa
        stft = librosa.stft(waveform, n_fft=1024, hop_length=512)
        magnitude = np.abs(stft) ** 2
        spectrogram_db = librosa.power_to_db(magnitude, ref=np.max)
        times_spec = librosa.frames_to_time(np.arange(spectrogram_db.shape[1]), sr=sample_rate, hop_length=512)
        freqs_spec = librosa.fft_frequencies(sr=sample_rate, n_fft=1024)
        ax_spec.pcolormesh(times_spec, freqs_spec, spectrogram_db, cmap='magma')
        ax_spec.set_title("Spectrogram")
        ax_spec.set_xlabel("Time (s)")
        ax_spec.set_ylabel("Frequency (Hz)")

        canvas = FigureCanvasTkAgg(fig, master=window)
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        canvas.draw_idle()

        self.waveform_window = window
        self.waveform_window_canvas = canvas
        self.waveform_progress_line = progress_line
        self.current_waveform_duration = duration
        window.protocol("WM_DELETE_WINDOW", self.close_waveform_window)

    def close_waveform_window(self):
        """Close the floating waveform window and stop monitoring."""
        self.stop_waveform_monitor()
        if self.waveform_window is not None:
            try:
                self.waveform_window.destroy()
            except tk.TclError:
                pass
        self.waveform_window = None
        self.waveform_window_canvas = None
        self.waveform_progress_line = None
        self.current_waveform_duration = None

    def stop_waveform_monitor(self):
        """Stop updating the waveform playback cursor."""
        if self.playback_monitor_id is not None:
            try:
                self.root.after_cancel(self.playback_monitor_id)
            except tk.TclError:
                pass
            self.playback_monitor_id = None

    def start_waveform_monitor(self):
        """Begin updating the waveform cursor to follow playback."""
        self.stop_waveform_monitor()
        if self.latest_waveform is None or self.latest_sample_rate is None:
            return
        self.playback_start_time = time.time()

        def update():
            if not pygame.mixer.get_init() or not pygame.mixer.music.get_busy():
                self.waveform_plotter.set_playback_cursor(self.waveform_plotter.waveform_duration)
                self.playback_monitor_id = None
                return
            elapsed = time.time() - (self.playback_start_time or time.time())
            duration = self.waveform_plotter.waveform_duration
            x = min(elapsed, duration)
            self.waveform_plotter.set_playback_cursor(x)
            self.playback_monitor_id = self.root.after(100, update)

        update()
    
    def set_status(self, message: str):
        """Update the status label."""
        self.status_var.set(message)
    
    def log(self, message: str):
        """Add a message to the log."""
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)


def main():
    """Main entry point for the GUI application."""
    root = tk.Tk()
    app = QWaveGUI(root)
    root.mainloop()


if __name__ == '__main__':
    main()
