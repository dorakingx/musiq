export type GateType = "H" | "X" | "Y" | "Z" | "T" | "S" | "CNOT" | "CZ" | "M";

export interface SingleQubitGate {
  column: number;
  type: GateType;
  qubit: number;
}

export interface TwoQubitGate {
  column: number;
  type: "CNOT" | "CZ";
  control: number;
  target: number;
}

export type CircuitGate = SingleQubitGate | TwoQubitGate;

export interface GeneratePayload {
  num_qubits: number;
  gates: CircuitGate[];
  duration: number;
  sample_rate: number;
  shots: number;
  backend: string;
}

export interface SpectrumPreview {
  frequencies_hz: number[];
  magnitude_db: number[];
}

export interface GenerateResult {
  audio_base64: string;
  sample_rate: number;
  duration: number;
  waveform_preview: number[];
  spectrum_preview: SpectrumPreview;
  analysis: Record<string, number>;
  analysis_report: string;
  backend: {
    requested: string;
    effective: string;
    requested_label?: string;
    effective_label: string;
    warning?: string | null;
  };
  logs: string[];
  measurement_outcomes: number;
  saved_audio_filename: string;
}

export const BACKEND_OPTIONS = [
  { value: "aer_simulator", label: "Local Aer Simulator (Default)" },
  { value: "ionq_simulator", label: "IonQ Simulator" },
  { value: "ionq_qpu", label: "IonQ QPU (Hardware)" },
] as const;

export const GATE_OPTIONS: { type: GateType; label: string }[] = [
  { type: "H", label: "H (Hadamard)" },
  { type: "X", label: "X (Pauli-X)" },
  { type: "Y", label: "Y (Pauli-Y)" },
  { type: "Z", label: "Z (Pauli-Z)" },
  { type: "T", label: "T (Phase)" },
  { type: "S", label: "S (Phase)" },
  { type: "CNOT", label: "CNOT (Entanglement)" },
  { type: "CZ", label: "CZ (Controlled-Z)" },
  { type: "M", label: "M (Measurement)" },
];

export const GATE_COLORS: Record<string, string> = {
  H: "#4CAF50",
  X: "#F44336",
  Y: "#FF9800",
  Z: "#2196F3",
  T: "#9C27B0",
  S: "#00BCD4",
  CNOT: "#E91E63",
  CZ: "#673AB7",
  M: "#607D8B",
};

export const SAMPLE_RATES = [22050, 44100, 48000, 96000] as const;
export const MIN_QUBITS = 2;
export const MAX_QUBITS = 10;
export const MIN_DURATION = 0.5;
export const MAX_DURATION = 60;
export const MIN_SHOTS = 128;
export const MAX_SHOTS = 8192;
