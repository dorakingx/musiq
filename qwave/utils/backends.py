"""
Execution backend definitions for local Aer and IonQ resources.
"""

from pathlib import Path
from typing import Dict, List, Optional, Tuple

from dotenv import load_dotenv

_QWAVE_PKG = Path(__file__).resolve().parent.parent
_REPO_ROOT = _QWAVE_PKG.parent if (_QWAVE_PKG.parent / "pyproject.toml").is_file() else Path.cwd()
load_dotenv(_REPO_ROOT / ".env")

BACKEND_AER = "aer_simulator"
BACKEND_IONQ_SIMULATOR = "ionq_simulator"
BACKEND_IONQ_QPU = "ionq_qpu"

BACKEND_LABELS_LOCAL: Dict[str, str] = {
    BACKEND_AER: "Local Aer Simulator (Default)",
    BACKEND_IONQ_SIMULATOR: "IonQ Simulator",
    BACKEND_IONQ_QPU: "IonQ QPU (Hardware)",
}

# Web API uses ideal Statevector simulation (no qiskit-aer), not Aer.
BACKEND_LABELS_WEB: Dict[str, str] = {
    BACKEND_AER: "Local Ideal Simulator (Default)",
    BACKEND_IONQ_SIMULATOR: "IonQ Simulator",
    BACKEND_IONQ_QPU: "IonQ QPU (Hardware)",
}

# Alias for desktop GUI / CLI (local Aer).
BACKEND_LABELS = BACKEND_LABELS_LOCAL

BACKEND_CHOICES: List[Tuple[str, str]] = [
    (BACKEND_AER, BACKEND_LABELS_LOCAL[BACKEND_AER]),
    (BACKEND_IONQ_SIMULATOR, BACKEND_LABELS_LOCAL[BACKEND_IONQ_SIMULATOR]),
    (BACKEND_IONQ_QPU, BACKEND_LABELS_LOCAL[BACKEND_IONQ_QPU]),
]

BACKEND_CLI_CHOICES = [key for key, _ in BACKEND_CHOICES]


def get_backend_label(backend_type: str, *, web: bool = False) -> str:
    labels = BACKEND_LABELS_WEB if web else BACKEND_LABELS_LOCAL
    return labels.get(backend_type, backend_type)


def parse_backend_type(value: Optional[str]) -> str:
    if value is None:
        return BACKEND_AER
    normalized = value.strip().lower()
    aliases = {
        "aer": BACKEND_AER,
        "local": BACKEND_AER,
        "ionq": BACKEND_IONQ_SIMULATOR,
        "simulator": BACKEND_IONQ_SIMULATOR,
        "qpu": BACKEND_IONQ_QPU,
        "hardware": BACKEND_IONQ_QPU,
    }
    if normalized in BACKEND_LABELS_LOCAL:
        return normalized
    return aliases.get(normalized, BACKEND_AER)
