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

export interface GenerateResult {
  audio_base64: string;
  sample_rate: number;
  duration: number;
  waveform_preview: number[];
  analysis: Record<string, number>;
  backend: {
    requested: string;
    effective: string;
    effective_label: string;
    warning?: string | null;
  };
  logs: string[];
  measurement_outcomes: number;
}

export const BACKEND_OPTIONS = [
  { value: "aer_simulator", label: "Local Ideal Simulator (Default)" },
  { value: "ionq_simulator", label: "IonQ Simulator (desktop app)" },
  { value: "ionq_qpu", label: "IonQ QPU (desktop app)" },
] as const;

export const GATE_OPTIONS: { type: GateType; label: string }[] = [
  { type: "H", label: "H" },
  { type: "X", label: "X" },
  { type: "Y", label: "Y" },
  { type: "Z", label: "Z" },
  { type: "T", label: "T" },
  { type: "S", label: "S" },
  { type: "CNOT", label: "CNOT" },
  { type: "CZ", label: "CZ" },
  { type: "M", label: "Measure" },
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
