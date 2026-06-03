import { MAX_QUBITS } from "@/lib/types";

export type CircuitEditorMode = "visual" | "qasm";

export interface TemplateSummary {
  id: string;
  filename: string;
  label: string;
  num_qubits: number;
  file_size_bytes?: number;
  /** False when the QASM file is too large to load in the browser API. */
  loadable?: boolean;
}

export interface TemplateListResponse {
  ok: boolean;
  templates?: TemplateSummary[];
  error?: string;
}

export interface TemplateGetResponse {
  ok: boolean;
  filename?: string;
  label?: string;
  num_qubits?: number;
  qasm?: string;
  error?: string;
}

export const VISUAL_MAX_QUBITS = MAX_QUBITS;
export const LARGE_CIRCUIT_QUBIT_WARNING = 24;

const QREG_PATTERN = /qreg\s+q\[(\d+)\]/i;

export function canUseVisualView(numQubits: number): boolean {
  return numQubits > 0 && numQubits <= VISUAL_MAX_QUBITS;
}

export function parseQubitCountFromQasm(qasm: string): number | null {
  const match = QREG_PATTERN.exec(qasm);
  if (!match) return null;
  const count = Number.parseInt(match[1], 10);
  return Number.isFinite(count) ? count : null;
}

export function countQasmLines(qasm: string): number {
  return qasm.split(/\r?\n/).length;
}
