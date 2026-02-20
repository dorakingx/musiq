"""
Q-Wave Project Constants

Configuration constants for audio processing, quantum circuits, and effects.
"""

# Audio Processing Constants
SAMPLING_RATE = 44100  # Sampling frequency (Hz)
DEFAULT_DURATION = 2.0  # Default audio duration (seconds)

# Quantum Circuit Constants
DEFAULT_N_QUBITS = 8  # Default number of qubits
DEFAULT_SHOTS = 1024  # Default number of measurement shots

# Audio Effect Constants
DEFAULT_ROOM_SIZE = 0.3  # Default reverb room size
DEFAULT_ATTACK_TIME = 0.05  # Default attack time (seconds)
DEFAULT_DECAY_TIME = 0.1    # Default decay time (seconds)
DEFAULT_SUSTAIN_LEVEL = 0.7  # Default sustain level
DEFAULT_RELEASE_TIME = 0.3   # Default release time (seconds)

# Tone Parameter Constants
BASE_FREQUENCY = 440  # Base frequency (A4 note)
HARMONIC_GAIN = 0.3   # Harmonic strength
MODULATION_FREQ_BASE = 10  # Modulation frequency base
MODULATION_FREQ_OFFSET = 2  # Modulation frequency offset
AMPLITUDE_MOD_BASE = 0.5   # Amplitude modulation base
AMPLITUDE_MOD_RANGE = 0.5   # Amplitude modulation range
FM_WAVE_GAIN = 0.2         # Frequency modulation gain
FREQ_DEV_RANGE = 8         # Frequency deviation range
FREQ_DEV_OFFSET = 4        # Frequency deviation offset

# GUI Constants
DEFAULT_WINDOW_WIDTH = 1400
DEFAULT_WINDOW_HEIGHT = 900
DEFAULT_CIRCUIT_BUILDER_QUBITS = 5

# Output Constants
DEFAULT_OUTPUT_DIR = "output"
DEFAULT_GENERATED_AUDIO_DIR = "generated_audio"
