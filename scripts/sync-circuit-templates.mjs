/**
 * Copy web-loadable QASM templates into public/ for Vercel serverless.
 * Run automatically before `next build` (see package.json prebuild).
 */
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.join(__dirname, "..");
const SOURCE_DIR = path.join(ROOT, "circuits");
const OUT_DIR = path.join(ROOT, "public", "circuit-templates");
const MAX_BYTES = 2 * 1024 * 1024;
const QREG = /qreg\s+q\[(\d+)\]/i;

const LABEL_OVERRIDES = {
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

const CATEGORY_ORDER = {
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

function categoryKey(stem) {
  if (stem.startsWith("quantum_walk")) return "quantum_walk";
  if (stem.startsWith("iqp") || stem === "example_iqp_4q") return "iqp";
  for (const prefix of ["bell", "ghz", "simple", "ring", "cx", "example", "hadamard", "mixed"]) {
    if (stem.startsWith(prefix)) return prefix;
  }
  return "other";
}

function labelFromStem(stem, numQubits) {
  if (LABEL_OVERRIDES[stem]) return LABEL_OVERRIDES[stem];
  const title = stem
    .split("_")
    .map((p) => p.charAt(0).toUpperCase() + p.slice(1))
    .join(" ");
  return numQubits != null ? `${title} (${numQubits}Q)` : title;
}

function parseQubits(snippet) {
  const m = QREG.exec(snippet);
  return m ? Number.parseInt(m[1], 10) : 0;
}

function readHead(filePath) {
  const fd = fs.openSync(filePath, "r");
  try {
    const buf = Buffer.alloc(8192);
    const n = fs.readSync(fd, buf, 0, buf.length, 0);
    return buf.toString("utf-8", 0, n);
  } finally {
    fs.closeSync(fd);
  }
}

if (!fs.existsSync(SOURCE_DIR)) {
  console.warn("[sync-circuit-templates] No circuits/ directory, skipping.");
  process.exit(0);
}

const existingManifest = path.join(OUT_DIR, "manifest.json");

fs.mkdirSync(OUT_DIR, { recursive: true });

for (const name of fs.readdirSync(OUT_DIR)) {
  if (name.endsWith(".qasm")) {
    fs.unlinkSync(path.join(OUT_DIR, name));
  }
}

const templates = [];

for (const name of fs.readdirSync(SOURCE_DIR)) {
  if (!name.endsWith(".qasm")) continue;
  const src = path.join(SOURCE_DIR, name);
  if (!fs.statSync(src).isFile()) continue;

  const size = fs.statSync(src).size;
  const stem = name.slice(0, -5);
  const numQubits = parseQubits(readHead(src));
  const loadable = size <= MAX_BYTES;

  if (loadable) {
    fs.copyFileSync(src, path.join(OUT_DIR, name));
  }

  templates.push({
    id: stem,
    filename: name,
    label: labelFromStem(stem, numQubits),
    num_qubits: numQubits,
    file_size_bytes: size,
    loadable,
  });
}

templates.sort((a, b) => {
  const ka = CATEGORY_ORDER[categoryKey(a.id)] ?? 99;
  const kb = CATEGORY_ORDER[categoryKey(b.id)] ?? 99;
  return ka - kb || a.num_qubits - b.num_qubits || a.id.localeCompare(b.id);
});

if (templates.length === 0) {
  if (fs.existsSync(existingManifest)) {
    console.warn(
      "[sync-circuit-templates] No .qasm files in circuits/; keeping existing manifest.",
    );
    process.exit(0);
  }
  console.error("[sync-circuit-templates] No templates found and no manifest to keep.");
  process.exit(1);
}

fs.writeFileSync(
  existingManifest,
  JSON.stringify({ ok: true, templates }, null, 2),
);

const copied = templates.filter((t) => t.loadable).length;
console.log(
  `[sync-circuit-templates] ${copied} loadable / ${templates.length} listed → public/circuit-templates/`,
);
