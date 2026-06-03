"""List and read OpenQASM templates from the circuits/ directory."""

from __future__ import annotations

import os
import re
from typing import Any, Dict, List, Optional

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
CIRCUITS_DIR = os.path.join(ROOT, "circuits")

QREG_PATTERN = re.compile(r"qreg\s+q\[(\d+)\]", re.IGNORECASE)

LABEL_OVERRIDES: Dict[str, str] = {
    "bell_2q": "Bell State (2Q)",
    "ghz_3q": "GHZ State (3Q)",
    "simple_entangled_3q": "Simple Entangled (3Q)",
    "ring_entangle_4q": "Ring Entangle (4Q)",
    "cx_control_high_2q": "CX Control High (2Q)",
    "example_iqp_4q": "Example IQP (4Q)",
    "iqp_like_4q": "IQP-like (4Q)",
    "iqp_8q": "IQP Circuit (8Q)",
    "iqp_16q": "IQP Circuit (16Q)",
    "iqp_20q": "IQP Circuit (20Q)",
    "iqp_24q": "IQP Circuit (24Q)",
    "iqp_56q": "IQP Circuit (56Q)",
    "quantum_walk_8q": "Quantum Walk (8Q)",
    "quantum_walk_16q": "Quantum Walk (16Q)",
    "quantum_walk_20q": "Quantum Walk (20Q)",
    "quantum_walk_24q": "Quantum Walk (24Q)",
    "quantum_walk_56q": "Quantum Walk (56Q)",
    "hadamard_all_measure_8q": "Hadamard + Measure (8Q)",
    "mixed_gates_5q": "Mixed Gates (5Q)",
}

# Lower = earlier in dropdown
CATEGORY_ORDER = {
    "bell": 0,
    "ghz": 1,
    "simple": 2,
    "ring": 3,
    "cx": 4,
    "example": 5,
    "iqp": 10,
    "quantum_walk": 20,
    "hadamard": 30,
    "mixed": 31,
    "other": 50,
}


def _category_key(stem: str) -> str:
    if stem.startswith("quantum_walk"):
        return "quantum_walk"
    if stem.startswith("iqp") or stem == "example_iqp_4q":
        return "iqp"
    for prefix in ("bell", "ghz", "simple", "ring", "cx", "example", "hadamard", "mixed"):
        if stem.startswith(prefix):
            return prefix
    return "other"


def _parse_qubits_from_qasm(qasm: str) -> Optional[int]:
    match = QREG_PATTERN.search(qasm)
    if match:
        return int(match.group(1))
    return None


def _label_from_stem(stem: str, num_qubits: Optional[int]) -> str:
    if stem in LABEL_OVERRIDES:
        return LABEL_OVERRIDES[stem]
    parts = stem.replace("_", " ").split()
    title = " ".join(p.capitalize() for p in parts)
    if num_qubits is not None:
        return f"{title} ({num_qubits}Q)"
    return title


def _sort_key(stem: str, num_qubits: int) -> tuple:
    category = _category_key(stem)
    return (CATEGORY_ORDER.get(category, 99), num_qubits, stem)


def _validate_filename(filename: str) -> str:
    base = os.path.basename(filename)
    if not base or base != filename:
        raise ValueError("Invalid template filename.")
    if not base.endswith(".qasm"):
        raise ValueError("Template must be a .qasm file.")
    if ".." in base:
        raise ValueError("Invalid template filename.")
    return base


def list_templates() -> List[Dict[str, Any]]:
    if not os.path.isdir(CIRCUITS_DIR):
        raise FileNotFoundError(f"Circuits directory not found: {CIRCUITS_DIR}")

    entries: List[Dict[str, Any]] = []
    for name in os.listdir(CIRCUITS_DIR):
        if not name.endswith(".qasm"):
            continue
        path = os.path.join(CIRCUITS_DIR, name)
        if not os.path.isfile(path):
            continue
        with open(path, encoding="utf-8") as handle:
            qasm = handle.read()
        stem = name[:-5]
        num_qubits = _parse_qubits_from_qasm(qasm) or 0
        entries.append(
            {
                "id": stem,
                "filename": name,
                "label": _label_from_stem(stem, num_qubits),
                "num_qubits": num_qubits,
            }
        )

    entries.sort(key=lambda item: _sort_key(item["id"], item["num_qubits"]))
    return entries


def read_template(filename: str) -> Dict[str, Any]:
    safe_name = _validate_filename(filename)
    path = os.path.join(CIRCUITS_DIR, safe_name)
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Template not found: {safe_name}")

    with open(path, encoding="utf-8") as handle:
        qasm = handle.read()

    stem = safe_name[:-5]
    num_qubits = _parse_qubits_from_qasm(qasm) or 0
    return {
        "filename": safe_name,
        "label": _label_from_stem(stem, num_qubits),
        "num_qubits": num_qubits,
        "qasm": qasm,
    }
