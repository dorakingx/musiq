import fs from "fs";
import path from "path";

import { isTemplateVisibleInWebView } from "@/lib/circuitTemplates";

/** Repo source (local dev). */
export const CIRCUITS_DIR = path.join(process.cwd(), "circuits");

/** Bundled for Vercel — populated by `npm run build` (prebuild sync). */
export const WEB_TEMPLATES_DIR = path.join(process.cwd(), "public", "circuit-templates");

const MANIFEST_PATH = path.join(WEB_TEMPLATES_DIR, "manifest.json");

function hasWebManifest(): boolean {
  return fs.existsSync(MANIFEST_PATH);
}

function readManifest(): TemplateCatalogEntry[] {
  const raw = JSON.parse(fs.readFileSync(MANIFEST_PATH, "utf-8")) as {
    templates?: TemplateCatalogEntry[];
  };
  return raw.templates ?? [];
}

function resolveReadPath(safeName: string): string {
  const webPath = path.join(WEB_TEMPLATES_DIR, safeName);
  if (fs.existsSync(webPath)) return webPath;
  const repoPath = path.join(CIRCUITS_DIR, safeName);
  if (fs.existsSync(repoPath)) return repoPath;
  throw new Error(`Template not found: ${safeName}`);
}

/** Max QASM file size served to the browser (larger files are listed but not loadable). */
export const MAX_TEMPLATE_BYTES = 2 * 1024 * 1024;

const QREG_PATTERN = /qreg\s+q\[(\d+)\]/i;

const LABEL_OVERRIDES: Record<string, string> = {
  bell_2q: "Bell State (2Q)",
  ghz_3q: "GHZ State (3Q)",
  simple_entangled_3q: "Simple Entangled (3Q)",
  ring_entangle_4q: "Ring Entangle (4Q)",
  cx_control_high_2q: "CX Control High (2Q)",
  example_iqp_4q: "Example IQP (4Q)",
  iqp_like_4q: "IQP-like (4Q)",
  iqp_8q: "IQP Circuit (8Q)",
  iqp_16q: "IQP Circuit (16Q)",
  iqp_20q: "IQP Circuit (20Q)",
  iqp_24q: "IQP Circuit (24Q)",
  iqp_56q: "IQP Circuit (56Q)",
  quantum_walk_8q: "Quantum Walk (8Q)",
  quantum_walk_16q: "Quantum Walk (16Q)",
  quantum_walk_20q: "Quantum Walk (20Q)",
  quantum_walk_24q: "Quantum Walk (24Q)",
  quantum_walk_56q: "Quantum Walk (56Q)",
  hadamard_all_measure_8q: "Hadamard + Measure (8Q)",
  mixed_gates_5q: "Mixed Gates (5Q)",
};

const CATEGORY_ORDER: Record<string, number> = {
  bell: 0,
  ghz: 1,
  simple: 2,
  ring: 3,
  cx: 4,
  example: 5,
  iqp: 10,
  quantum_walk: 20,
  hadamard: 30,
  mixed: 31,
  other: 50,
};

export interface TemplateCatalogEntry {
  id: string;
  filename: string;
  label: string;
  num_qubits: number;
  file_size_bytes: number;
  loadable: boolean;
  /** False when the lattice cannot faithfully render the template (e.g. quantum walk). */
  visual_preview: boolean;
}

/** Templates built from custom gate definitions / multi-controlled X are QASM-only on the canvas. */
export function supportsVisualPreview(templateId: string): boolean {
  return !templateId.startsWith("quantum_walk");
}

function enrichEntry(
  entry: Omit<TemplateCatalogEntry, "visual_preview"> & { visual_preview?: boolean },
): TemplateCatalogEntry {
  return {
    ...entry,
    visual_preview: entry.visual_preview ?? supportsVisualPreview(entry.id),
  };
}

function categoryKey(stem: string): string {
  if (stem.startsWith("quantum_walk")) return "quantum_walk";
  if (stem.startsWith("iqp") || stem === "example_iqp_4q") return "iqp";
  for (const prefix of ["bell", "ghz", "simple", "ring", "cx", "example", "hadamard", "mixed"]) {
    if (stem.startsWith(prefix)) return prefix;
  }
  return "other";
}

export function parseQubitsFromQasmSnippet(qasm: string): number | null {
  const match = QREG_PATTERN.exec(qasm);
  if (!match) return null;
  const count = Number.parseInt(match[1], 10);
  return Number.isFinite(count) ? count : null;
}

function labelFromStem(stem: string, numQubits: number | null): string {
  if (stem in LABEL_OVERRIDES) return LABEL_OVERRIDES[stem];
  const title = stem
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
  if (numQubits !== null) return `${title} (${numQubits}Q)`;
  return title;
}

function sortKey(stem: string, numQubits: number): [number, number, string] {
  return [CATEGORY_ORDER[categoryKey(stem)] ?? 99, numQubits, stem];
}

export function validateTemplateFilename(filename: string): string {
  const base = path.basename(filename);
  if (!base || base !== filename) {
    throw new Error("Invalid template filename.");
  }
  if (!base.endsWith(".qasm")) {
    throw new Error("Template must be a .qasm file.");
  }
  if (base.includes("..")) {
    throw new Error("Invalid template filename.");
  }
  return base;
}

function readQregSnippet(filePath: string): string {
  const fd = fs.openSync(filePath, "r");
  try {
    const buffer = Buffer.alloc(8192);
    const bytesRead = fs.readSync(fd, buffer, 0, buffer.length, 0);
    return buffer.toString("utf-8", 0, bytesRead);
  } finally {
    fs.closeSync(fd);
  }
}

export function listTemplateCatalog(): TemplateCatalogEntry[] {
  if (hasWebManifest()) {
    return readManifest()
      .map((entry) => enrichEntry(entry))
      .filter(isTemplateVisibleInWebView);
  }

  if (!fs.existsSync(CIRCUITS_DIR)) {
    throw new Error(
      `Circuits directory not found. Run "node scripts/sync-circuit-templates.mjs" or npm run build.`,
    );
  }

  const entries: TemplateCatalogEntry[] = [];
  for (const name of fs.readdirSync(CIRCUITS_DIR)) {
    if (!name.endsWith(".qasm")) continue;
    const filePath = path.join(CIRCUITS_DIR, name);
    if (!fs.statSync(filePath).isFile()) continue;

    const fileSize = fs.statSync(filePath).size;
    const snippet = readQregSnippet(filePath);
    const stem = name.slice(0, -5);
    const numQubits = parseQubitsFromQasmSnippet(snippet) ?? 0;
    const loadable = fileSize <= MAX_TEMPLATE_BYTES;

    entries.push(
      enrichEntry({
        id: stem,
        filename: name,
        label: labelFromStem(stem, numQubits),
        num_qubits: numQubits,
        file_size_bytes: fileSize,
        loadable,
      }),
    );
  }

  entries.sort((a, b) => {
    const ka = sortKey(a.id, a.num_qubits);
    const kb = sortKey(b.id, b.num_qubits);
    return ka[0] - kb[0] || ka[1] - kb[1] || ka[2].localeCompare(kb[2]);
  });

  return entries.filter(isTemplateVisibleInWebView);
}

export function readTemplateFile(filename: string): {
  filename: string;
  label: string;
  num_qubits: number;
  qasm: string;
} {
  const safeName = validateTemplateFilename(filename);

  if (hasWebManifest()) {
    const entry = readManifest().find((item) => item.filename === safeName);
    if (!entry) {
      throw new Error(`Template not found: ${safeName}`);
    }
    if (!entry.loadable) {
      const sizeMb = (entry.file_size_bytes / (1024 * 1024)).toFixed(1);
      throw new Error(
        `Template "${safeName}" is too large for the web editor (${sizeMb} MB). ` +
          `Use a smaller example or load it via the CLI (qwave_run.py).`,
      );
    }
  }

  const filePath = resolveReadPath(safeName);
  const fileSize = fs.statSync(filePath).size;
  if (fileSize > MAX_TEMPLATE_BYTES) {
    const sizeMb = (fileSize / (1024 * 1024)).toFixed(1);
    throw new Error(
      `Template "${safeName}" is too large for the web editor (${sizeMb} MB). ` +
        `Use a smaller example or load it via the CLI (qwave_run.py).`,
    );
  }

  const qasm = fs.readFileSync(filePath, "utf-8");
  const stem = safeName.slice(0, -5);
  const numQubits = parseQubitsFromQasmSnippet(qasm) ?? 0;

  return {
    filename: safeName,
    label: labelFromStem(stem, numQubits),
    num_qubits: numQubits,
    qasm,
  };
}
