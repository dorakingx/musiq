#!/usr/bin/env python3
"""
Q-Wave GUI Application

A graphical user interface for building quantum circuits and generating
non-classical audio patterns. Users can visually construct quantum circuits
and listen to the generated quantum audio in real-time.
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
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import time

from qwave.gui.circuit_builder import CircuitBuilderWidget
from qwave.modules.simulator import QuantumSimulator
from qwave.modules.generator import AudioGenerator
from qwave.modules.analyzer import SpectralAnalyzer


class QWaveGUI:
    """
    Main GUI application for Q-Wave quantum audio generation.
    """
    
    def __init__(self, root):
        """Initialize the GUI application."""
        self.root = root
        self.root.title("Q-Wave: Quantum Circuit Audio Generator")
        self.root.geometry("1200x800")
        
        # Initialize pygame for audio playback
        pygame.mixer.init()
        
        # Current audio file path
        self.current_audio_path = None
        self.latest_waveform = None
        self.latest_sample_rate = None
        self.is_generating = False
        self.output_dir = tk.StringVar(
            value=str((Path.cwd() / "generated_audio").resolve())
        )
        self.waveform_window = None
        self.waveform_window_canvas = None
        self.waveform_progress_line = None
        self.playback_monitor_id = None
        self.current_waveform_duration = None
        self.playback_start_time = None
        
        # Create UI
        self.create_widgets()
        
        # Set default values
        self.duration_var.set(5.0)
        self.sample_rate_var.set(44100)
        self.shots_var.set(1024)
    
    def create_widgets(self):
        """Create and layout all GUI widgets."""
        # Main container
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(1, weight=1)
        
        # Left panel: Gate selection and controls
        left_panel = ttk.Frame(main_frame)
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
        self.num_qubits_var = tk.IntVar(value=5)
        qubits_spin = ttk.Spinbox(params_frame, from_=2, to=10, 
                                  textvariable=self.num_qubits_var,
                                  command=self.update_num_qubits, width=10)
        qubits_spin.pack(anchor=tk.W, pady=(0, 10))
        
        # Audio generation parameters
        audio_frame = ttk.LabelFrame(left_panel, text="Audio Parameters", padding="10")
        audio_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Duration
        ttk.Label(audio_frame, text="Duration (seconds):").pack(anchor=tk.W)
        self.duration_var = tk.DoubleVar(value=5.0)
        duration_spin = ttk.Spinbox(audio_frame, from_=0.5, to=60.0, increment=0.5,
                                   textvariable=self.duration_var, width=10)
        duration_spin.pack(anchor=tk.W, pady=(0, 5))
        
        # Sample rate
        ttk.Label(audio_frame, text="Sample Rate (Hz):").pack(anchor=tk.W)
        self.sample_rate_var = tk.IntVar(value=44100)
        sample_rate_combo = ttk.Combobox(audio_frame, textvariable=self.sample_rate_var,
                                        values=[22050, 44100, 48000, 96000], width=10)
        sample_rate_combo.pack(anchor=tk.W, pady=(0, 5))
        
        # Shots
        ttk.Label(audio_frame, text="Measurement Shots:").pack(anchor=tk.W)
        self.shots_var = tk.IntVar(value=1024)
        shots_spin = ttk.Spinbox(audio_frame, from_=128, to=8192, increment=128,
                               textvariable=self.shots_var, width=10)
        shots_spin.pack(anchor=tk.W, pady=(0, 10))
        
        # Output settings
        output_frame = ttk.LabelFrame(left_panel, text="Output Settings", padding="10")
        output_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(output_frame, text="Auto-Save Folder:").pack(anchor=tk.W)
        output_entry = ttk.Entry(output_frame, textvariable=self.output_dir, state='readonly', width=28)
        output_entry.pack(anchor=tk.W, pady=(0, 5), fill=tk.X)
        ttk.Button(output_frame, text="Change Folder", command=self.choose_output_dir).pack(fill=tk.X)
        
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
        
        # Center: Circuit builder
        center_frame = ttk.Frame(main_frame)
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
        
        # Right panel: Status and analysis
        right_panel = ttk.Frame(main_frame)
        right_panel.grid(row=0, column=2, rowspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))
        right_panel.columnconfigure(0, weight=1)
        right_panel.rowconfigure(1, weight=1)
        
        # Status label
        self.status_label = ttk.Label(right_panel, text="Ready", 
                                      font=('Arial', 10, 'bold'))
        self.status_label.pack(pady=(0, 10))
        
        # Progress bar
        self.progress = ttk.Progressbar(right_panel, mode='indeterminate')
        self.progress.pack(fill=tk.X, pady=(0, 10))
        
        # Analysis output
        analysis_label = ttk.Label(right_panel, text="Analysis Output")
        analysis_label.pack(anchor=tk.W, pady=(0, 5))
        
        self.analysis_text = scrolledtext.ScrolledText(
            right_panel, width=40, height=30, wrap=tk.WORD
        )
        self.analysis_text.pack(fill=tk.BOTH, expand=True)
        
        waveform_frame = ttk.LabelFrame(right_panel, text="Waveform", padding="5")
        waveform_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
        self.waveform_figure = Figure(figsize=(4, 3), dpi=100)
        self.waveform_ax = self.waveform_figure.add_subplot(211)
        self.spectrum_ax = self.waveform_figure.add_subplot(212)
        self.waveform_ax.set_title("Waveform")
        self.waveform_ax.set_xlabel("Time (s)")
        self.waveform_ax.set_ylabel("Amplitude")
        self.spectrum_ax.set_title("Magnitude Spectrum")
        self.spectrum_ax.set_xlabel("Frequency (Hz)")
        self.spectrum_ax.set_ylabel("Magnitude (dB)")
        self.waveform_canvas = FigureCanvasTkAgg(self.waveform_figure, master=waveform_frame)
        self.waveform_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        self.clear_waveform_plot()
        
        # Bottom: Log output
        log_frame = ttk.LabelFrame(main_frame, text="Log", padding="5")
        log_frame.grid(row=1, column=1, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(10, 0))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=8, wrap=tk.WORD)
        self.log_text.pack(fill=tk.BOTH, expand=True)
    
    def on_gate_selected(self):
        """Handle gate selection."""
        gate_type = self.selected_gate.get()
        self.circuit_builder.set_selected_gate(gate_type)
        self.log(f"Selected gate: {gate_type}")
    
    def update_num_qubits(self):
        """Update the number of qubits in the circuit."""
        num_qubits = self.num_qubits_var.get()
        # Recreate circuit builder with new number of qubits
        # This is a simplified approach - in production, you'd update the existing widget
        self.log(f"Number of qubits changed to {num_qubits}")
        # Note: Full implementation would require recreating the widget
    
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
                self.root.after(0, self.progress.start)
                
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
                
                # Save circuit to temporary QASM file
                temp_qasm = tempfile.NamedTemporaryFile(mode='w', suffix='.qasm', delete=False)
                temp_qasm.write(dumps(circuit))
                temp_qasm.close()
                
                # Run simulation
                self.root.after(0, self.log, "Running quantum simulation...")
                simulator = QuantumSimulator(shots=shots)
                simulator.load_circuit_from_qasm(temp_qasm.name)
                measurement_results = simulator.execute_simulation()
                statevector = simulator.get_statevector()
                probability_dist = simulator.get_probability_distribution()
                measurement_sequence = simulator.get_measurement_sequence()
                
                self.root.after(0, self.log, f"Simulation completed: {len(measurement_results)} outcomes")
                
                # Generate audio
                self.root.after(0, self.log, "Generating audio waveform...")
                audio_generator = AudioGenerator(sample_rate=sample_rate)
                waveform = audio_generator.map_quantum_to_audio(
                    statevector=statevector,
                    measurement_sequence=measurement_sequence,
                    probability_distribution=probability_dist,
                    duration=duration
                )
                
                # Save to output directory
                output_dir = Path(self.output_dir.get())
                output_dir.mkdir(parents=True, exist_ok=True)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = output_dir / f"qwave_{timestamp}.wav"
                audio_generator.save_wav(waveform, filename)
                self.current_audio_path = str(filename)
                self.latest_waveform = waveform
                self.latest_sample_rate = sample_rate
                
                # Perform analysis
                self.root.after(0, self.log, "Performing spectral analysis...")
                analyzer = SpectralAnalyzer(sample_rate=sample_rate)
                analysis_results = analyzer.analyze(waveform)
                
                # Display analysis
                self.root.after(0, self.display_analysis, analysis_results)
                
                # Cleanup
                os.unlink(temp_qasm.name)
                
                self.root.after(0, self.set_status, "Audio generated successfully!")
                self.root.after(0, self.log, f"Audio saved to: {filename}")
                self.root.after(0, self.show_waveform)
                
            except Exception as e:
                self.root.after(0, messagebox.showerror, "Error", f"Failed to generate audio: {str(e)}")
                self.root.after(0, self.log, f"Error: {str(e)}")
            finally:
                def finish():
                    self.progress.stop()
                    self.is_generating = False
                self.root.after(0, finish)
        
        thread = threading.Thread(target=generate, daemon=True)
        thread.start()
    
    def display_analysis(self, results: dict):
        """Display spectral analysis results."""
        self.analysis_text.delete(1.0, tk.END)
        
        text = "=" * 50 + "\n"
        text += "QUANTUM AUDIO SPECTRAL ANALYSIS\n"
        text += "=" * 50 + "\n\n"
        
        text += "--- Basic Spectral Features ---\n"
        text += f"Spectral Centroid:      {results['spectral_centroid_hz']:.2f} Hz\n"
        text += f"Spectral Bandwidth:     {results['spectral_bandwidth_hz']:.2f} Hz\n"
        text += f"Spectral Rolloff:       {results['spectral_rolloff_hz']:.2f} Hz\n"
        text += f"Spectral Flatness:      {results['spectral_flatness']:.4f}\n\n"
        
        text += "--- Non-Stationarity Analysis ---\n"
        text += f"Non-Stationarity Index: {results['non_stationarity_index']:.4f}\n"
        text += f"Temporal Variation:     {results['temporal_variation']:.4f}\n\n"
        
        text += "--- Modulation Characteristics ---\n"
        text += f"Modulation Depth:              {results['modulation_depth']:.4f}\n"
        text += f"Frequency Modulation Index:    {results['frequency_modulation_index']:.4f}\n"
        text += f"Avg Spectral Spread:           {results['average_spectral_spread_hz']:.2f} Hz\n"
        text += f"Spectral Spread Variation:     {results['spectral_spread_variation']:.4f}\n\n"
        
        text += "--- Quantum Pattern Indicators ---\n"
        text += f"Spectral Entropy:        {results['spectral_entropy']:.4f}\n"
        text += f"Phase Coherence:        {results['phase_coherence']:.4f}\n"
        text += f"Periodicity Strength:   {results['periodicity_strength']:.4f}\n"
        text += f"Quantum Likelihood:     {results['quantum_likelihood_score']:.4f}\n"
        
        self.analysis_text.insert(1.0, text)
    
    def play_audio(self):
        """Play the generated audio."""
        if self.current_audio_path is None:
            messagebox.showwarning("No Audio", "Please generate audio first.")
            return
        if not os.path.exists(self.current_audio_path):
            messagebox.showerror("Missing File", "The generated audio file could not be found.")
            return
        waveform = self.latest_waveform
        sample_rate = self.latest_sample_rate
        if (waveform is None or sample_rate is None) and self.current_audio_path:
            try:
                waveform, sample_rate = sf.read(self.current_audio_path)
                self.latest_waveform = waveform
                self.latest_sample_rate = sample_rate
            except Exception as exc:
                messagebox.showerror("Error", f"Failed to load audio for playback: {exc}")
                self.log(f"Error loading audio: {exc}")
                return
        
        try:
            target_rate = int(sample_rate) if sample_rate else 44100
            if pygame.mixer.get_init():
                pygame.mixer.quit()
            pygame.mixer.init(frequency=target_rate)
            pygame.mixer.music.load(self.current_audio_path)
            pygame.mixer.music.set_volume(1.0)
            pygame.mixer.music.play()
            self.log("Playing audio...")
            self.set_status("Playing audio...")
            if waveform is not None and sample_rate:
                self.update_waveform_plot(waveform, sample_rate)
                self.open_waveform_window(waveform, sample_rate)
                self.start_waveform_monitor()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to play audio: {str(e)}")
            self.log(f"Error playing audio: {str(e)}")
    
    def stop_audio(self):
        """Stop audio playback."""
        if pygame.mixer.get_init():
            pygame.mixer.music.stop()
        self.stop_waveform_monitor()
        if self.waveform_progress_line is not None and self.current_waveform_duration is not None:
            self.waveform_progress_line.set_xdata([self.current_waveform_duration,
                                                   self.current_waveform_duration])
            if self.waveform_window_canvas:
                self.waveform_window_canvas.draw_idle()
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
    
    def load_circuit(self):
        """Load a quantum circuit from a QASM file."""
        filename = filedialog.askopenfilename(
            filetypes=[("QASM files", "*.qasm"), ("All files", "*.*")]
        )
        
        if filename:
            try:
                simulator = QuantumSimulator()
                circuit = simulator.load_circuit_from_qasm(filename)

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
    
    def set_status(self, message: str):
        """Update the status label."""
        self.status_label.config(text=message)
    
    def log(self, message: str):
        """Add a message to the log."""
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
    
    def choose_output_dir(self):
        """Allow user to select output directory for auto-saved audio files."""
        directory = filedialog.askdirectory(initialdir=self.output_dir.get())
        if directory:
            self.output_dir.set(directory)
            self.log(f"Output folder set to: {directory}")
    
    def clear_waveform_plot(self):
        """Clear the waveform plot."""
        self.waveform_ax.clear()
        self.waveform_ax.set_title("Waveform")
        self.waveform_ax.set_xlabel("Time (s)")
        self.waveform_ax.set_ylabel("Amplitude")
        self.spectrum_ax.clear()
        self.spectrum_ax.set_title("Magnitude Spectrum")
        self.spectrum_ax.set_xlabel("Frequency (Hz)")
        self.spectrum_ax.set_ylabel("Magnitude (dB)")
        self.waveform_canvas.draw_idle()
    
    def update_waveform_plot(self, waveform: np.ndarray, sample_rate: int):
        """Update waveform plot with provided data."""
        if waveform is None or sample_rate is None:
            return
        if waveform.ndim > 1:
            waveform = np.mean(waveform, axis=1)
        duration = len(waveform) / sample_rate
        time_axis = np.linspace(0, duration, len(waveform))
        max_points = 5000
        if len(waveform) > max_points:
            indices = np.linspace(0, len(waveform) - 1, max_points).astype(int)
            waveform = waveform[indices]
            time_axis = time_axis[indices]
        self.waveform_ax.clear()
        self.waveform_ax.plot(time_axis, waveform, linewidth=0.8)
        self.waveform_ax.set_title("Waveform")
        self.waveform_ax.set_xlabel("Time (s)")
        self.waveform_ax.set_ylabel("Amplitude")
        self.waveform_ax.margins(x=0)
        freq_axis = np.fft.rfftfreq(len(waveform), d=1 / sample_rate)
        spectrum = np.abs(np.fft.rfft(waveform))
        spectrum = 20 * np.log10(spectrum + 1e-9)
        self.spectrum_ax.clear()
        self.spectrum_ax.plot(freq_axis, spectrum, color='#ff7043', linewidth=0.8)
        self.spectrum_ax.set_xlim(0, min(10000, freq_axis[-1]))
        self.spectrum_ax.set_ylim(np.max(spectrum) - 80, np.max(spectrum) + 5)
        self.spectrum_ax.set_xlabel("Frequency (Hz)")
        self.spectrum_ax.set_ylabel("Magnitude (dB)")
        self.spectrum_ax.grid(True, linestyle='--', linewidth=0.5, alpha=0.6)
        self.waveform_canvas.draw_idle()
    
    def show_waveform(self):
        """Display waveform for current audio."""
        waveform = self.latest_waveform
        sample_rate = self.latest_sample_rate
        if waveform is None and self.current_audio_path:
            try:
                waveform, sample_rate = sf.read(self.current_audio_path)
            except Exception as exc:
                self.log(f"Unable to load waveform: {exc}")
                return
        if waveform is not None and sample_rate:
            self.update_waveform_plot(waveform, sample_rate)

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

        fig = Figure(figsize=(8, 3), dpi=100)
        ax_wave = fig.add_subplot(211)
        ax_spec = fig.add_subplot(212)
        ax_wave.plot(time_axis, waveform, linewidth=0.8)
        ax_wave.set_title("Audio Waveform")
        ax_wave.set_xlabel("Time (s)")
        ax_wave.set_ylabel("Amplitude")
        ax_wave.margins(x=0)
        progress_line = ax_wave.axvline(0, color='red', linewidth=1, label='Playback Position')
        ax_spec.specgram(waveform, NFFT=1024, Fs=sample_rate, noverlap=512, cmap='magma')
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
        if self.waveform_window is None or self.waveform_progress_line is None:
            return
        self.playback_start_time = time.time()

        def update():
            if self.waveform_window is None or self.waveform_progress_line is None:
                self.playback_monitor_id = None
                return
            if not pygame.mixer.get_init() or not pygame.mixer.music.get_busy():
                x = self.current_waveform_duration or 0
                self.waveform_progress_line.set_xdata([x, x])
                if self.waveform_window_canvas:
                    self.waveform_window_canvas.draw_idle()
                self.playback_monitor_id = None
                return
            elapsed = time.time() - (self.playback_start_time or time.time())
            duration = self.current_waveform_duration or 0
            x = min(elapsed, duration)
            self.waveform_progress_line.set_xdata([x, x])
            if self.waveform_window_canvas:
                self.waveform_window_canvas.draw_idle()
            self.playback_monitor_id = self.root.after(100, update)

        update()


def main():
    """Main entry point for the GUI application."""
    root = tk.Tk()
    app = QWaveGUI(root)
    root.mainloop()


if __name__ == '__main__':
    main()

