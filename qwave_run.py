#!/usr/bin/env python3
"""
Q-Wave Local CUI Tool - Main Entry Point

This script provides a command-line interface for generating audio waveforms
from quantum circuits. It loads quantum circuits from QASM files, executes
simulations, and generates WAV audio files with non-classical patterns.
"""

import argparse
import sys
import os
from pathlib import Path

from qwave.modules.simulator import QuantumSimulator
from qwave.modules.generator import AudioGenerator
from qwave.modules.analyzer import SpectralAnalyzer


def main():
    """
    Main entry point for the Q-Wave CUI tool.
    """
    parser = argparse.ArgumentParser(
        description='Q-Wave: Generate non-classical audio patterns from quantum circuits',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python qwave_run.py -c circuits/iqp_10q.qasm -o results/q_sound_01.wav
  python qwave_run.py -c my_circuit.qasm -o output.wav -d 3 -shots 4096
  python qwave_run.py -c circuit.qasm -o sound.wav -s 48000 -d 10
        """
    )
    
    # Required arguments
    parser.add_argument(
        '-c', '--circuit',
        type=str,
        required=True,
        help='Path to input quantum circuit file (QASM format)'
    )
    
    parser.add_argument(
        '-o', '--output',
        type=str,
        required=True,
        help='Path to output WAV file'
    )
    
    # Optional arguments
    parser.add_argument(
        '-d', '--duration',
        type=float,
        default=5.0,
        help='Duration of generated audio in seconds (default: 5.0)'
    )
    
    parser.add_argument(
        '-s', '--samplerate',
        type=int,
        default=44100,
        help='Audio sample rate in Hz (default: 44100)'
    )
    
    parser.add_argument(
        '-shots', '--shots',
        type=int,
        default=1024,
        help='Number of quantum measurement shots (default: 1024)'
    )
    
    parser.add_argument(
        '--no-analysis',
        action='store_true',
        help='Skip spectral analysis (faster execution)'
    )
    
    args = parser.parse_args()
    
    # Validate arguments
    if not os.path.exists(args.circuit):
        print(f"Error: Circuit file not found: {args.circuit}", file=sys.stderr)
        sys.exit(1)
    
    if args.duration <= 0:
        print("Error: Duration must be positive", file=sys.stderr)
        sys.exit(1)
    
    if args.samplerate <= 0:
        print("Error: Sample rate must be positive", file=sys.stderr)
        sys.exit(1)
    
    if args.shots <= 0:
        print("Error: Number of shots must be positive", file=sys.stderr)
        sys.exit(1)
    
    # Create output directory if it doesn't exist
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    print("=" * 60)
    print("Q-Wave: Quantum Circuit to Audio Generator")
    print("=" * 60)
    print(f"Circuit file:     {args.circuit}")
    print(f"Output file:      {args.output}")
    print(f"Duration:         {args.duration} seconds")
    print(f"Sample rate:      {args.samplerate} Hz")
    print(f"Measurement shots: {args.shots}")
    print("=" * 60)
    print()
    
    try:
        # Step 1: Load and simulate quantum circuit
        print("Step 1: Loading quantum circuit...")
        simulator = QuantumSimulator(shots=args.shots)
        circuit = simulator.load_circuit_from_qasm(args.circuit)
        
        circuit_info = simulator.get_circuit_info()
        print(f"  ✓ Circuit loaded: {circuit_info['num_qubits']} qubits, depth {circuit_info['depth']}")
        
        print("\nStep 2: Executing quantum simulation...")
        measurement_results = simulator.execute_simulation()
        print(f"  ✓ Simulation completed: {len(measurement_results)} unique measurement outcomes")
        
        print("\nStep 3: Extracting quantum state information...")
        statevector = simulator.get_statevector()
        probability_dist = simulator.get_probability_distribution()
        measurement_sequence = simulator.get_measurement_sequence()
        print(f"  ✓ Statevector extracted: {statevector.shape[0]} states")
        print(f"  ✓ Probability distribution computed")
        
        # Step 2: Generate audio waveform
        print("\nStep 4: Generating audio waveform from quantum patterns...")
        audio_generator = AudioGenerator(sample_rate=args.samplerate)
        waveform = audio_generator.map_quantum_to_audio(
            statevector=statevector,
            measurement_sequence=measurement_sequence,
            probability_distribution=probability_dist,
            duration=args.duration
        )
        print(f"  ✓ Audio waveform generated: {len(waveform)} samples")
        
        # Step 3: Save WAV file
        print("\nStep 5: Saving audio to WAV file...")
        audio_generator.save_wav(waveform, args.output)
        print(f"  ✓ Audio saved successfully")
        
        # Step 4: Perform spectral analysis
        if not args.no_analysis:
            print("\nStep 6: Performing spectral analysis...")
            analyzer = SpectralAnalyzer(sample_rate=args.samplerate)
            analysis_results = analyzer.analyze(waveform)
            analyzer.print_analysis_report(analysis_results)
        else:
            print("\nStep 6: Spectral analysis skipped (--no-analysis flag)")
        
        print("\n" + "=" * 60)
        print("SUCCESS: Quantum audio generation completed!")
        print("=" * 60)
        print(f"Output file: {args.output}")
        print("=" * 60 + "\n")
        
    except FileNotFoundError as e:
        print(f"\nError: {e}", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"\nError: {e}", file=sys.stderr)
        sys.exit(1)
    except RuntimeError as e:
        print(f"\nError: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()

