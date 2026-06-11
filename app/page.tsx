"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  BACKEND_OPTIONS,
  GATE_COLORS,
  GATE_OPTIONS,
  MAX_DURATION,
  MAX_QUBITS,
  MAX_SHOTS,
  MIN_DURATION,
  MIN_QUBITS,
  MIN_SHOTS,
  SAMPLE_RATES,
  type CircuitGate,
  type GateType,
  type GenerateResult,
} from "@/lib/types";
import {
  canUseVisualView,
  isTemplateVisibleInWebView,
  countQasmLines,
  LARGE_CIRCUIT_QUBIT_WARNING,
  parseQubitCountFromQasm,
  type CircuitEditorMode,
  type TemplateSummary,
} from "@/lib/circuitTemplates";
import { drawWaveformPanel } from "@/lib/waveformPlot";
import { AudioPlayer } from "@/app/components/AudioPlayer";
import { ResearchDrawer } from "@/app/components/ResearchDrawer";

const COLUMN_WIDTH = 70;
const QUBIT_SPACING = 56;
const LEFT_MARGIN = 50;
const TOP_MARGIN = 30;

const CIRCUIT = {
  gridEven: "rgba(255, 255, 255, 0.07)",
  gridOdd: "rgba(255, 255, 255, 0.03)",
  columnLabel: "#6b7694",
  qubitLabel: "#a8b4d4",
  qubitLine: "#3d4668",
  gateFill: "#12151f",
};

const GATE_SHORT_NAMES: Record<GateType, string> = {
  H: "Hadamard",
  X: "Pauli-X",
  Y: "Pauli-Y",
  Z: "Pauli-Z",
  T: "Phase",
  S: "Phase",
  CNOT: "Entangle",
  CZ: "Ctrl-Z",
  M: "Measure",
};

function base64ToBlob(base64: string, mimeType: string) {
  const binary = atob(base64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i += 1) {
    bytes[i] = binary.charCodeAt(i);
  }
  return new Blob([bytes], { type: mimeType });
}

function gatesToPayload(gates: CircuitGate[]) {
  return gates.map((gate) => ({ ...gate }));
}

function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

function gateAtPosition(gates: CircuitGate[], column: number, qubit: number, type: GateType) {
  return gates.find((gate) => {
    if ("control" in gate) {
      return (
        gate.column === column &&
        gate.type === type &&
        (gate.control === qubit || gate.target === qubit)
      );
    }
    return gate.column === column && gate.qubit === qubit && gate.type === type;
  });
}

async function parseTemplatesResponse(response: Response) {
  const text = await response.text();
  try {
    return JSON.parse(text) as Record<string, unknown>;
  } catch {
    throw new Error(
      response.status === 404
        ? "Template API not found. Restart the dev server (npm run dev) and try again."
        : `Template API returned an invalid response (HTTP ${response.status}).`,
    );
  }
}

export default function HomePage() {
  const [numQubits, setNumQubits] = useState(3);
  const [selectedGate, setSelectedGate] = useState<GateType>("H");
  const [gates, setGates] = useState<CircuitGate[]>([]);
  const [duration, setDuration] = useState(2);
  const [sampleRate, setSampleRate] = useState(44100);
  const [shots, setShots] = useState(1024);
  const [backend, setBackend] = useState("aer_simulator");
  const [status, setStatus] = useState("Ready");
  const [logs, setLogs] = useState<string[]>([]);
  const [isGenerating, setIsGenerating] = useState(false);
  const [result, setResult] = useState<GenerateResult | null>(null);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [hoverCell, setHoverCell] = useState<{ column: number; qubit: number } | null>(null);
  const [playbackTime, setPlaybackTime] = useState<number>(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [researchOpen, setResearchOpen] = useState(false);
  const timeCanvasRef = useRef<HTMLCanvasElement | null>(null);
  const spectrumCanvasRef = useRef<HTMLCanvasElement | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const qasmInputRef = useRef<HTMLInputElement | null>(null);
  const [editorMode, setEditorMode] = useState<CircuitEditorMode>("visual");
  const [qasmText, setQasmText] = useState("");
  const [activeTemplateId, setActiveTemplateId] = useState<string | null>(null);
  const [templates, setTemplates] = useState<TemplateSummary[]>([]);
  const [templatesLoading, setTemplatesLoading] = useState(true);
  const [templateSelectValue, setTemplateSelectValue] = useState("");
  const [templateLoading, setTemplateLoading] = useState(false);
  const [visualPreviewNote, setVisualPreviewNote] = useState<string | null>(null);
  const generationIdRef = useRef(0);
  const abortRef = useRef<AbortController | null>(null);
  const playbackFrameRef = useRef<number | null>(null);

  const maxColumn = useMemo(() => {
    if (gates.length === 0) return 4;
    return Math.max(4, ...gates.map((gate) => gate.column + 1));
  }, [gates]);

  const gridColumns = Math.max(maxColumn + 2, 6);
  const svgWidth = LEFT_MARGIN + gridColumns * COLUMN_WIDTH + 40;
  const svgHeight = TOP_MARGIN + numQubits * QUBIT_SPACING + 24;

  const qasmQubitCount = useMemo(
    () => parseQubitCountFromQasm(qasmText),
    [qasmText],
  );

  const inferredQubitCount =
    qasmText.trim() && qasmQubitCount !== null ? qasmQubitCount : numQubits;

  const effectiveQubitCount = inferredQubitCount;

  const visualViewAllowed = canUseVisualView(inferredQubitCount);

  const qasmLineCount = useMemo(() => countQasmLines(qasmText), [qasmText]);

  const appendLog = useCallback((message: string) => {
    setLogs((prev) => [...prev, message]);
  }, []);

  const cancelGeneration = useCallback(
    (reason: string) => {
      if (!isGenerating && !abortRef.current) return;
      generationIdRef.current += 1;
      abortRef.current?.abort();
      abortRef.current = null;
      setIsGenerating(false);
      appendLog(`Cancelled ongoing generation: ${reason}`);
      setStatus("Ready");
    },
    [appendLog, isGenerating],
  );

  useEffect(() => {
    return () => {
      if (audioUrl) URL.revokeObjectURL(audioUrl);
      abortRef.current?.abort();
    };
  }, [audioUrl]);

  useEffect(() => {
    if (!timeCanvasRef.current || !spectrumCanvasRef.current) return;
    drawWaveformPanel(
      timeCanvasRef.current,
      spectrumCanvasRef.current,
      result,
      playbackTime,
    );
  }, [result, playbackTime]);

  const redrawPlots = useCallback(() => {
    if (timeCanvasRef.current && spectrumCanvasRef.current) {
      drawWaveformPanel(timeCanvasRef.current, spectrumCanvasRef.current, result, playbackTime);
    }
  }, [result, playbackTime]);

  useEffect(() => {
    const onResize = () => redrawPlots();
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, [redrawPlots]);

  useEffect(() => {
    const loadTemplates = async () => {
      try {
        const response = await fetch("/api/templates", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ action: "list" }),
        });
        const payload = await parseTemplatesResponse(response);
        if (!response.ok || !payload.ok) {
          throw new Error(String(payload.error || "Failed to load templates."));
        }
        const listed = (payload.templates as TemplateSummary[]) ?? [];
        setTemplates(listed.filter(isTemplateVisibleInWebView));
      } catch (error) {
        const message = error instanceof Error ? error.message : "Unknown error";
        appendLog(`Template catalog unavailable: ${message}`);
      } finally {
        setTemplatesLoading(false);
      }
    };
    void loadTemplates();
  }, [appendLog]);

  const importQasmToVisual = useCallback(
    async (qasm: string) => {
      const response = await fetch("/api/circuit", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "import", qasm }),
      });
      const payload = await response.json();
      if (!response.ok || !payload.ok) {
        throw new Error(payload.error || "Import failed.");
      }
      const importedQubits = payload.num_qubits as number;
      if (!canUseVisualView(importedQubits)) {
        throw new Error(
          `Circuit has ${importedQubits} qubits; visual editor supports up to ${MAX_QUBITS}.`,
        );
      }
      setNumQubits(importedQubits);
      setGates(payload.gates);
      return importedQubits;
    },
    [],
  );

  const exportVisualToQasm = useCallback(async () => {
    if (gates.length === 0) {
      return "";
    }
    const response = await fetch("/api/circuit", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        action: "export",
        num_qubits: numQubits,
        gates: gatesToPayload(gates),
      }),
    });
    const payload = await response.json();
    if (!response.ok || !payload.ok) {
      throw new Error(payload.error || "Export failed.");
    }
    return payload.qasm as string;
  }, [gates, numQubits]);

  const switchEditorMode = useCallback(
    async (mode: CircuitEditorMode) => {
      if (mode === editorMode) return;

      if (mode === "qasm") {
        try {
          const exported = await exportVisualToQasm();
          setQasmText(exported);
          setEditorMode("qasm");
          appendLog(
            exported
              ? "Exported visual circuit to QASM editor."
              : "QASM editor ready — paste or load a circuit.",
          );
        } catch (error) {
          const message = error instanceof Error ? error.message : "Unknown error";
          window.alert(`Failed to export circuit: ${message}`);
        }
        return;
      }

      const qubits = qasmQubitCount ?? parseQubitCountFromQasm(qasmText);
      if (qubits !== null && !canUseVisualView(qubits)) {
        window.alert(
          `This circuit has ${qubits} qubits. The visual editor supports up to ${MAX_QUBITS} qubits. Use Code (QASM) view instead.`,
        );
        return;
      }

      if (!qasmText.trim()) {
        setEditorMode("visual");
        appendLog("Switched to visual editor.");
        return;
      }

      try {
        await importQasmToVisual(qasmText);
        setEditorMode("visual");
        appendLog("Imported QASM into visual canvas.");
      } catch (error) {
        const message = error instanceof Error ? error.message : "Unknown error";
        window.alert(`Failed to import QASM into visual editor: ${message}`);
      }
    },
    [
      appendLog,
      editorMode,
      exportVisualToQasm,
      importQasmToVisual,
      qasmQubitCount,
      qasmText,
    ],
  );

  const loadTemplate = useCallback(
    async (filename: string) => {
      const catalogEntry = templates.find((entry) => entry.filename === filename);
      if (catalogEntry?.loadable === false) {
        const sizeMb = ((catalogEntry.file_size_bytes ?? 0) / (1024 * 1024)).toFixed(1);
        window.alert(
          `"${catalogEntry.label}" is too large for the web editor (${sizeMb} MB). ` +
            "Choose a smaller example, or use qwave_run.py with this QASM file.",
        );
        setTemplateSelectValue("");
        return;
      }

      setTemplateLoading(true);
      setStatus("Loading template...");
      try {
        const response = await fetch("/api/templates", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ action: "get", filename }),
        });
        const payload = await parseTemplatesResponse(response);
        if (!response.ok || !payload.ok) {
          throw new Error(String(payload.error || "Failed to load template."));
        }

        const qasm = payload.qasm as string;
        const label = payload.label as string;
        const numTemplateQubits = payload.num_qubits as number;

        setQasmText(qasm);
        const templateId = filename.replace(/\.qasm$/, "");
        setActiveTemplateId(templateId);

        const visualPreviewSupported = catalogEntry?.visual_preview !== false;

        if (canUseVisualView(numTemplateQubits)) {
          setNumQubits(numTemplateQubits);

          if (visualPreviewSupported) {
            try {
              const response = await fetch("/api/circuit", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ action: "import", qasm }),
              });
              const importPayload = await response.json();
              if (!response.ok || !importPayload.ok) {
                throw new Error(importPayload.error || "Import failed.");
              }
              const importedGates = (importPayload.gates as CircuitGate[]) ?? [];
              setGates(importedGates);
              if (importedGates.length === 0) {
                setVisualPreviewNote(
                  "This template could not be drawn on the visual lattice (unsupported or composite gates). Use Code (QASM) view for the full circuit, or switch to Code view and click Generate audio.",
                );
                appendLog(
                  `Loaded template: ${label} (QASM ready — visual lattice is empty for this program).`,
                );
              } else {
                setVisualPreviewNote(null);
                appendLog(`Loaded template: ${label} (visual canvas updated).`);
              }
            } catch {
              setGates([]);
              setVisualPreviewNote(
                "Visual import failed for this template. Use Code (QASM) view to inspect and run the circuit.",
              );
              appendLog(
                `Loaded template: ${label} (QASM stored — open Code view to edit or generate).`,
              );
            }
          } else {
            setGates([]);
            setVisualPreviewNote(
              "Quantum Walk templates use custom multi-controlled gates. They cannot be shown on the visual lattice — open Code (QASM) view, then click Generate audio.",
            );
            appendLog(
              `Loaded template: ${label} (QASM ready — Quantum Walk is Code view / generate only on the lattice).`,
            );
          }
        } else {
          setGates([]);
          setVisualPreviewNote(null);
          appendLog(
            `Loaded template: ${label} (${numTemplateQubits}Q, visual canvas unavailable).`,
          );
        }

        setStatus(`Template loaded: ${label}`);

        if (numTemplateQubits >= LARGE_CIRCUIT_QUBIT_WARNING) {
          appendLog(
            `Note: ${numTemplateQubits}-qubit circuits may take longer to simulate in the browser API.`,
          );
        }
      } catch (error) {
        const message = error instanceof Error ? error.message : "Unknown error";
        setStatus("Template load failed");
        appendLog(`Template load error: ${message}`);
        window.alert(`Failed to load template: ${message}`);
      } finally {
        setTemplateLoading(false);
        setTemplateSelectValue("");
      }
    },
    [appendLog, importQasmToVisual, templates],
  );

  const stopPlaybackMonitor = () => {
    if (playbackFrameRef.current !== null) {
      cancelAnimationFrame(playbackFrameRef.current);
      playbackFrameRef.current = null;
    }
  };

  const startPlaybackMonitor = () => {
    const tick = () => {
      if (!audioRef.current || audioRef.current.paused) {
        stopPlaybackMonitor();
        return;
      }
      setPlaybackTime(audioRef.current.currentTime);
      playbackFrameRef.current = requestAnimationFrame(tick);
    };
    stopPlaybackMonitor();
    playbackFrameRef.current = requestAnimationFrame(tick);
  };

  const pauseAudio = () => {
    const audio = audioRef.current;
    if (audio) {
      audio.pause();
      setPlaybackTime(audio.currentTime);
    }
    stopPlaybackMonitor();
    setIsPlaying(false);
    setStatus("Ready");
  };

  const togglePlayPause = () => {
    if (!audioUrl) {
      window.alert("Please generate audio first.");
      return;
    }
    const audio = audioRef.current;
    if (!audio) return;

    if (!audio.paused) {
      pauseAudio();
      appendLog("Audio paused");
      return;
    }

    void audio.play();
    setIsPlaying(true);
    appendLog("Playing audio...");
    setStatus("Playing audio...");
    startPlaybackMonitor();
  };

  const seekAudio = (time: number) => {
    const audio = audioRef.current;
    if (!audio || !result?.duration) return;
    const clamped = Math.max(0, Math.min(time, result.duration));
    audio.currentTime = clamped;
    setPlaybackTime(clamped);
  };

  const clearCircuit = () => {
    setGates([]);
    setQasmText("");
    setActiveTemplateId(null);
    setVisualPreviewNote(null);
    appendLog("Circuit cleared");
  };

  const removeGateAt = (column: number, qubit: number) => {
    setGates((prev) =>
      prev.filter((gate) => {
        if ("control" in gate) {
          return !(
            gate.column === column &&
            (gate.control === qubit || gate.target === qubit)
          );
        }
        return !(gate.column === column && gate.qubit === qubit);
      }),
    );
  };

  const placeGate = (column: number, qubit: number) => {
    if (editorMode === "qasm" && qasmText.trim()) {
      setQasmText("");
      setActiveTemplateId(null);
      setVisualPreviewNote(null);
    }
    if (selectedGate === "CNOT" || selectedGate === "CZ") {
      if (qubit >= numQubits - 1) return;
      if (gateAtPosition(gates, column, qubit, selectedGate)) {
        removeGateAt(column, qubit);
        appendLog(`Removed ${selectedGate} at q${qubit}, column ${column}.`);
        return;
      }
      const next: CircuitGate = {
        column,
        type: selectedGate,
        control: qubit,
        target: qubit + 1,
      };
      setGates((prev) => {
        const filtered = prev.filter(
          (gate) =>
            !(
              "control" in gate &&
              gate.column === column &&
              (gate.control === qubit || gate.target === qubit + 1)
            ),
        );
        return [...filtered, next];
      });
      appendLog(`Placed ${selectedGate} on q${qubit}–q${qubit + 1}, column ${column}.`);
      return;
    }

    if (gateAtPosition(gates, column, qubit, selectedGate)) {
      removeGateAt(column, qubit);
      appendLog(`Removed ${selectedGate} at q${qubit}, column ${column}.`);
      return;
    }

    const next: CircuitGate = { column, type: selectedGate, qubit };
    setGates((prev) => {
      const filtered = prev.filter(
        (gate) =>
          !(
            !("control" in gate) &&
            gate.column === column &&
            gate.qubit === qubit
          ),
      );
      return [...filtered, next];
    });
    appendLog(`Placed ${selectedGate} on q${qubit}, column ${column}.`);
  };

  const handleCircuitClick = (event: React.MouseEvent<SVGSVGElement>) => {
    const rect = event.currentTarget.getBoundingClientRect();
    const x = event.clientX - rect.left - LEFT_MARGIN;
    const y = event.clientY - rect.top - TOP_MARGIN;
    if (x < 0 || y < 0) return;

    const column = Math.floor(x / COLUMN_WIDTH);
    const qubit = Math.floor(y / QUBIT_SPACING);
    if (qubit < 0 || qubit >= numQubits || column < 0) return;
    placeGate(column, qubit);
  };

  const handleCircuitMove = (event: React.MouseEvent<SVGSVGElement>) => {
    const rect = event.currentTarget.getBoundingClientRect();
    const x = event.clientX - rect.left - LEFT_MARGIN;
    const y = event.clientY - rect.top - TOP_MARGIN;
    if (x < 0 || y < 0) {
      setHoverCell(null);
      return;
    }
    const column = Math.floor(x / COLUMN_WIDTH);
    const qubit = Math.floor(y / QUBIT_SPACING);
    if (qubit < 0 || qubit >= numQubits || column < 0) {
      setHoverCell(null);
      return;
    }
    setHoverCell((prev) =>
      prev?.column === column && prev.qubit === qubit ? prev : { column, qubit },
    );
  };

  const handleBackendChange = (value: string) => {
    const label = BACKEND_OPTIONS.find((o) => o.value === value)?.label ?? value;
    if (isGenerating) {
      cancelGeneration(`Compute resource changed to ${label}`);
    }
    setBackend(value);
    setStatus(`Compute resource: ${label}`);
    appendLog(`Selected compute resource: ${label}`);
  };

  const generateAudio = async () => {
    const useQasmMode = editorMode === "qasm";
    if (useQasmMode) {
      if (!qasmText.trim()) {
        window.alert("Please enter or load QASM in the Code view first.");
        return;
      }
    } else if (gates.length === 0) {
      window.alert("Please add gates to the circuit first.");
      return;
    }

    if (isGenerating) {
      cancelGeneration("Starting a new generation");
    }

    generationIdRef.current += 1;
    const generationId = generationIdRef.current;
    const controller = new AbortController();
    abortRef.current = controller;

    setIsGenerating(true);
    setStatus("Generating audio...");
    appendLog(
      useQasmMode
        ? "Starting generation from QASM..."
        : "Starting generation from visual circuit...",
    );

    try {
      const requestBody = useQasmMode
        ? {
            qasm: qasmText,
            duration,
            sample_rate: sampleRate,
            shots,
            backend,
          }
        : {
            num_qubits: numQubits,
            gates: gatesToPayload(gates),
            duration,
            sample_rate: sampleRate,
            shots,
            backend,
          };

      const response = await fetch("/api/generate_audio", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(requestBody),
        signal: controller.signal,
      });

      const payload = await response.json();
      if (!response.ok || !payload.ok) {
        throw new Error(payload.error || "Generation failed.");
      }

      if (generationId !== generationIdRef.current) return;

      const nextResult = payload.result as GenerateResult;
      setResult(nextResult);
      nextResult.logs.forEach((line) => appendLog(line));

      const blob = base64ToBlob(nextResult.audio_base64, "audio/wav");
      const nextUrl = URL.createObjectURL(blob);
      setAudioUrl((prev) => {
        if (prev) URL.revokeObjectURL(prev);
        return nextUrl;
      });

      setPlaybackTime(0);
      setIsPlaying(false);
      setStatus("Audio generated successfully!");
      appendLog("Audio ready for playback. Use Save Audio to download when you want.");
    } catch (error) {
      if (generationId !== generationIdRef.current) return;
      if (error instanceof DOMException && error.name === "AbortError") {
        appendLog("Generation cancelled.");
        return;
      }
      const message = error instanceof Error ? error.message : "Unknown error";
      setStatus("Generation failed");
      appendLog(`Error: ${message}`);
      window.alert(`Failed to generate audio: ${message}`);
    } finally {
      if (generationId === generationIdRef.current) {
        setIsGenerating(false);
        abortRef.current = null;
      }
    }
  };

  const saveAudio = () => {
    if (!result?.audio_base64) {
      window.alert("Please generate audio first.");
      return;
    }
    const blob = base64ToBlob(result.audio_base64, "audio/wav");
    const filename = result.saved_audio_filename || "qwave_output.wav";
    downloadBlob(blob, filename);
    appendLog(`Audio saved to: ${filename}`);
    window.alert(`Audio saved to:\n${filename}`);
  };

  const saveCircuit = async () => {
    try {
      const response = await fetch("/api/circuit", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          action: "export",
          num_qubits: numQubits,
          gates: gatesToPayload(gates),
        }),
      });
      const payload = await response.json();
      if (!response.ok || !payload.ok) {
        throw new Error(payload.error || "Export failed.");
      }
      const blob = new Blob([payload.qasm], { type: "text/plain" });
      downloadBlob(blob, "circuit.qasm");
      appendLog("Circuit saved to: circuit.qasm");
      window.alert("Circuit saved to:\ncircuit.qasm");
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unknown error";
      window.alert(`Failed to save circuit: ${message}`);
    }
  };

  const loadCircuitFromFile = async (file: File) => {
    try {
      const qasm = await file.text();
      setQasmText(qasm);
      setActiveTemplateId(null);
      setEditorMode("qasm");

      const qubits = parseQubitCountFromQasm(qasm);
      if (qubits !== null && canUseVisualView(qubits)) {
        try {
          await importQasmToVisual(qasm);
          appendLog(`Circuit loaded from: ${file.name} (visual + QASM).`);
        } catch {
          setGates([]);
          appendLog(`Circuit loaded from: ${file.name} (QASM only).`);
        }
      } else {
        setGates([]);
        appendLog(`Circuit loaded from: ${file.name} (QASM — visual view unavailable).`);
      }

      if (qubits !== null && qubits >= LARGE_CIRCUIT_QUBIT_WARNING) {
        appendLog(`Note: ${qubits}-qubit circuits may take longer to simulate.`);
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unknown error";
      window.alert(`Failed to load circuit: ${message}`);
    }
  };

  const onGateSelected = (gateType: GateType) => {
    setSelectedGate(gateType);
    appendLog(`Selected gate: ${gateType}`);
  };

  const metricsText =
    result?.analysis_report ?? "Metrics will appear here after generation.";

  return (
    <main className="app-shell">
      <header className="hero">
        <div className="hero__brand">
          <div className="hero__logo-wrap">
            <img src="/musiq_logo.png" alt="Musiq" width={52} height={52} />
          </div>
          <div className="hero__titles">
            <h1>Musiq</h1>
            <p className="hero__tagline">
              Quantum circuits meet sonic sculpture — compose interference, render waveforms,
              listen to the non-classical.
            </p>
          </div>
        </div>
        <div className="hero__actions">
          <button
            type="button"
            className={`research-toggle ${researchOpen ? "research-toggle--active" : ""}`}
            onClick={() => setResearchOpen((prev) => !prev)}
            aria-expanded={researchOpen}
            aria-controls="research-drawer"
          >
            Analysis
          </button>
          <div className="hero__status">
            <span
              className={`hero__status-dot ${isGenerating ? "hero__status-dot--busy" : ""}`}
            />
            <span>{status}</span>
          </div>
        </div>
      </header>

      <ResearchDrawer
        open={researchOpen}
        onClose={() => setResearchOpen(false)}
        metricsText={metricsText}
        logs={logs}
      />

      <div className="grid">
        <section className="panel stack left-panel">
          <div className="card">
            <div className="card__head">
              <h3 className="card__title">Quantum Gates</h3>
              <span className="card__accent" />
            </div>
            <div className="gate-palette">
              {GATE_OPTIONS.map((gate) => (
                <button
                  key={gate.type}
                  type="button"
                  className={`gate-chip ${selectedGate === gate.type ? "gate-chip--active" : ""}`}
                  style={{ "--gate-color": GATE_COLORS[gate.type] } as React.CSSProperties}
                  onClick={() => onGateSelected(gate.type)}
                  title={gate.label}
                >
                  <span className="gate-chip__symbol">{gate.type}</span>
                  <span className="gate-chip__name">{GATE_SHORT_NAMES[gate.type]}</span>
                </button>
              ))}
            </div>
            <button
              className="btn-ghost btn-ghost--wide"
              type="button"
              onClick={clearCircuit}
              style={{ marginTop: 12 }}
            >
              Clear circuit
            </button>
          </div>

          <div className="card">
            <div className="card__head">
              <h3 className="card__title">Circuit</h3>
              <span className="card__accent" />
            </div>
            <div className="field">
              <label htmlFor="num-qubits">Qubits</label>
              <input
                id="num-qubits"
                type="number"
                min={MIN_QUBITS}
                max={MAX_QUBITS}
                value={numQubits}
                onChange={(event) => {
                  const value = Number(event.target.value);
                  setNumQubits(value);
                  appendLog(`Number of qubits changed to ${value}`);
                  setGates((prev) =>
                    prev.filter((gate) => {
                      if ("control" in gate) {
                        return gate.control < value && gate.target < value;
                      }
                      return gate.qubit < value;
                    }),
                  );
                }}
              />
            </div>
          </div>

          <div className="card">
            <div className="card__head">
              <h3 className="card__title">Compute</h3>
              <span className="card__accent" />
            </div>
            <div className="backend-list">
              {BACKEND_OPTIONS.map((option) => (
                <label key={option.value} className="backend-option">
                  <input
                    type="radio"
                    name="backend"
                    value={option.value}
                    checked={backend === option.value}
                    onChange={() => handleBackendChange(option.value)}
                  />
                  <span className="backend-option__body">{option.label}</span>
                </label>
              ))}
            </div>
          </div>

          <div className="card">
            <div className="card__head">
              <h3 className="card__title">Audio</h3>
              <span className="card__accent" />
            </div>
            <div className="field-grid">
              <div className="field-grid field-grid--compact">
                <div className="field">
                  <label htmlFor="duration">Duration (s)</label>
                  <input
                    id="duration"
                    type="number"
                    min={MIN_DURATION}
                    max={MAX_DURATION}
                    step={0.5}
                    value={duration}
                    onChange={(event) => setDuration(Number(event.target.value))}
                  />
                </div>
                <div className="field">
                  <label htmlFor="sample-rate">Sample rate</label>
                  <select
                    id="sample-rate"
                    value={sampleRate}
                    onChange={(event) => setSampleRate(Number(event.target.value))}
                  >
                    {SAMPLE_RATES.map((rate) => (
                      <option key={rate} value={rate}>
                        {rate.toLocaleString()} Hz
                      </option>
                    ))}
                  </select>
                </div>
              </div>
              <div className="field">
                <label htmlFor="shots">Shots</label>
                <input
                  id="shots"
                  type="number"
                  min={MIN_SHOTS}
                  max={MAX_SHOTS}
                  step={128}
                  value={shots}
                  onChange={(event) => setShots(Number(event.target.value))}
                />
              </div>
            </div>
          </div>

          <button
            className={`btn-generate ${isGenerating ? "btn-generate--loading" : ""}`}
            type="button"
            disabled={isGenerating}
            onClick={generateAudio}
          >
            {isGenerating ? "Synthesizing…" : "Generate audio"}
          </button>

        </section>

        <section className="panel stack center-panel">
          <div className="panel-header">
            <h2>Circuit editor</h2>
            <p className="hint">
              Build on the visual lattice or edit OpenQASM 2.0 directly — load examples, tweak
              gates, then generate audio.
            </p>
          </div>

          <div className="circuit-toolbar">
            <div className="editor-tabs" role="tablist" aria-label="Circuit editor mode">
              <button
                type="button"
                role="tab"
                aria-selected={editorMode === "visual"}
                className={`editor-tab ${editorMode === "visual" ? "editor-tab--active" : ""}`}
                disabled={!visualViewAllowed && qasmText.trim().length > 0}
                title={
                  !visualViewAllowed && qasmText.trim().length > 0
                    ? `Circuit has ${inferredQubitCount} qubits; visual editor supports up to ${MAX_QUBITS}`
                    : "Drag-and-drop gate canvas"
                }
                onClick={() => void switchEditorMode("visual")}
              >
                Visual view
              </button>
              <button
                type="button"
                role="tab"
                aria-selected={editorMode === "qasm"}
                className={`editor-tab ${editorMode === "qasm" ? "editor-tab--active" : ""}`}
                onClick={() => void switchEditorMode("qasm")}
              >
                Code (QASM) view
              </button>
            </div>

            <div className="template-select-wrap">
              <label htmlFor="template-select">Load example</label>
              <select
                id="template-select"
                className="template-select"
                value={templateSelectValue}
                disabled={templatesLoading || templateLoading || templates.length === 0}
                onChange={(event) => {
                  const filename = event.target.value;
                  if (filename) void loadTemplate(filename);
                }}
              >
                <option value="">
                  {templateLoading
                    ? "Loading circuit…"
                    : templatesLoading
                      ? "Loading templates…"
                      : templates.length === 0
                        ? "No templates available"
                        : "Choose a circuit…"}
                </option>
                {templates.map((template) => (
                  <option key={template.id} value={template.filename}>
                    {template.label}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {editorMode === "qasm" ? (
            <div className="qasm-editor-wrap">
              <div className="qasm-editor-meta">
                <span>
                  {qasmQubitCount !== null
                    ? `${qasmQubitCount} qubit${qasmQubitCount === 1 ? "" : "s"}`
                    : "Qubits: unknown"}
                </span>
                <span>{qasmLineCount} lines</span>
                {activeTemplateId ? <span>Template: {activeTemplateId}</span> : null}
              </div>
              <textarea
                className="qasm-editor"
                spellCheck={false}
                value={qasmText}
                placeholder="Paste or edit OpenQASM 2.0 here, or load an example from the dropdown."
                onChange={(event) => {
                  setQasmText(event.target.value);
                  setActiveTemplateId(null);
                }}
              />
            </div>
          ) : !visualViewAllowed ? (
            <div className="visual-disabled-overlay">
              This circuit has {effectiveQubitCount} qubits. The visual editor supports up to{" "}
              {MAX_QUBITS} qubits — switch to Code (QASM) view to edit and run it.
            </div>
          ) : (
          <div className="circuit-board">
            {visualPreviewNote ? (
              <div className="visual-preview-note">{visualPreviewNote}</div>
            ) : null}
            <svg
              className="circuit-svg"
              width={svgWidth}
              height={svgHeight}
              onClick={handleCircuitClick}
              onMouseMove={handleCircuitMove}
              onMouseLeave={() => setHoverCell(null)}
            >
              <defs>
                <filter id="gate-glow" x="-50%" y="-50%" width="200%" height="200%">
                  <feGaussianBlur stdDeviation="2" result="blur" />
                  <feMerge>
                    <feMergeNode in="blur" />
                    <feMergeNode in="SourceGraphic" />
                  </feMerge>
                </filter>
              </defs>

              {Array.from({ length: gridColumns + 1 }).map((_, col) => {
                const x = LEFT_MARGIN + col * COLUMN_WIDTH;
                const gridTop = TOP_MARGIN / 2;
                const gridBottom = TOP_MARGIN + numQubits * QUBIT_SPACING;
                return (
                  <g key={`col-${col}`}>
                    <line
                      x1={x}
                      y1={gridTop}
                      x2={x}
                      y2={gridBottom}
                      stroke={col % 2 === 0 ? CIRCUIT.gridEven : CIRCUIT.gridOdd}
                      strokeWidth={1}
                      strokeDasharray="2 4"
                    />
                    {col % 2 === 0 ? (
                      <text
                        x={x}
                        y={14}
                        fill={CIRCUIT.columnLabel}
                        fontSize="9"
                        textAnchor="middle"
                        fontFamily="var(--font-mono)"
                      >
                        {col}
                      </text>
                    ) : null}
                  </g>
                );
              })}

              {Array.from({ length: numQubits }).map((_, qubit) => {
                const y = TOP_MARGIN + qubit * QUBIT_SPACING + QUBIT_SPACING / 2;
                return (
                  <g key={`qubit-${qubit}`}>
                    <text
                      x={10}
                      y={y + 4}
                      fill={CIRCUIT.qubitLabel}
                      fontSize="11"
                      fontFamily="var(--font-mono)"
                    >{`q${qubit}`}</text>
                    <line
                      x1={LEFT_MARGIN}
                      y1={y}
                      x2={svgWidth - 20}
                      y2={y}
                      stroke={CIRCUIT.qubitLine}
                      strokeWidth={2}
                    />
                  </g>
                );
              })}

              {hoverCell ? (
                <g pointerEvents="none">
                  {selectedGate === "CNOT" || selectedGate === "CZ" ? (
                    hoverCell.qubit < numQubits - 1 ? (
                      <>
                        <line
                          x1={LEFT_MARGIN + hoverCell.column * COLUMN_WIDTH + COLUMN_WIDTH / 2}
                          y1={TOP_MARGIN + hoverCell.qubit * QUBIT_SPACING + QUBIT_SPACING / 2}
                          x2={LEFT_MARGIN + hoverCell.column * COLUMN_WIDTH + COLUMN_WIDTH / 2}
                          y2={
                            TOP_MARGIN +
                            (hoverCell.qubit + 1) * QUBIT_SPACING +
                            QUBIT_SPACING / 2
                          }
                          stroke={GATE_COLORS[selectedGate]}
                          strokeWidth={2}
                          strokeDasharray="4 4"
                          opacity={0.7}
                        />
                        <circle
                          cx={LEFT_MARGIN + hoverCell.column * COLUMN_WIDTH + COLUMN_WIDTH / 2}
                          cy={TOP_MARGIN + hoverCell.qubit * QUBIT_SPACING + QUBIT_SPACING / 2}
                          r={8}
                          fill="none"
                          stroke={GATE_COLORS[selectedGate]}
                          strokeWidth={2}
                          strokeDasharray="4 4"
                        />
                        <circle
                          cx={LEFT_MARGIN + hoverCell.column * COLUMN_WIDTH + COLUMN_WIDTH / 2}
                          cy={
                            TOP_MARGIN +
                            (hoverCell.qubit + 1) * QUBIT_SPACING +
                            QUBIT_SPACING / 2
                          }
                          r={8}
                          fill="none"
                          stroke={GATE_COLORS[selectedGate]}
                          strokeWidth={2}
                          strokeDasharray="4 4"
                        />
                      </>
                    ) : null
                  ) : (
                    <rect
                      x={LEFT_MARGIN + hoverCell.column * COLUMN_WIDTH + COLUMN_WIDTH / 2 - 18}
                      y={TOP_MARGIN + hoverCell.qubit * QUBIT_SPACING + QUBIT_SPACING / 2 - 16}
                      width={36}
                      height={32}
                      rx={4}
                      fill="none"
                      stroke={GATE_COLORS[selectedGate]}
                      strokeWidth={2}
                      strokeDasharray="3 3"
                      opacity={0.8}
                    />
                  )}
                </g>
              ) : null}

              {gates.map((gate, index) => {
                const x = LEFT_MARGIN + gate.column * COLUMN_WIDTH + COLUMN_WIDTH / 2;
                if ("control" in gate) {
                  const controlY = TOP_MARGIN + gate.control * QUBIT_SPACING + QUBIT_SPACING / 2;
                  const targetY = TOP_MARGIN + gate.target * QUBIT_SPACING + QUBIT_SPACING / 2;
                  const color = GATE_COLORS[gate.type];
                  return (
                    <g key={`${gate.type}-${gate.column}-${index}`}>
                      <line x1={x} y1={controlY} x2={x} y2={targetY} stroke={color} strokeWidth={2} filter="url(#gate-glow)" />
                      <circle cx={x} cy={controlY} r={8} fill={CIRCUIT.gateFill} stroke={color} strokeWidth={2} />
                      <circle cx={x} cy={targetY} r={8} fill={CIRCUIT.gateFill} stroke={color} strokeWidth={2} />
                      {gate.type === "CNOT" ? (
                        <>
                          <line x1={x - 8} y1={targetY} x2={x + 8} y2={targetY} stroke={color} />
                          <line x1={x} y1={targetY - 8} x2={x} y2={targetY + 8} stroke={color} />
                        </>
                      ) : null}
                    </g>
                  );
                }

                const y = TOP_MARGIN + gate.qubit * QUBIT_SPACING + QUBIT_SPACING / 2;
                const color = GATE_COLORS[gate.type];
                return (
                  <g key={`${gate.type}-${gate.column}-${gate.qubit}-${index}`}>
                    <rect
                      x={x - 18}
                      y={y - 16}
                      width={36}
                      height={32}
                      rx={6}
                      fill={CIRCUIT.gateFill}
                      stroke={color}
                      strokeWidth={2}
                      filter="url(#gate-glow)"
                    />
                    <text
                      x={x}
                      y={y + 5}
                      textAnchor="middle"
                      fill={color}
                      fontSize="13"
                      fontWeight="700"
                      fontFamily="var(--font-display)"
                    >
                      {gate.type}
                    </text>
                  </g>
                );
              })}
            </svg>
          </div>
          )}

          <div className="card">
            <div className="card__head">
              <h3 className="card__title">Output</h3>
              <span className="card__accent" />
            </div>
            <div className="waveform-stack">
              <div className="waveform-box">
                <canvas ref={timeCanvasRef} className="waveform-canvas" />
              </div>
              <div className="waveform-box">
                <canvas ref={spectrumCanvasRef} className="waveform-canvas" />
              </div>
            </div>
            <AudioPlayer
              disabled={!audioUrl}
              isPlaying={isPlaying}
              playbackTime={playbackTime}
              duration={result?.duration ?? 0}
              canSave={Boolean(result?.audio_base64)}
              onPlayPause={togglePlayPause}
              onSeek={seekAudio}
              onSaveAudio={saveAudio}
              onLoadQasm={() => qasmInputRef.current?.click()}
              onExportCircuit={() => void saveCircuit()}
              qasmInputRef={qasmInputRef}
              onQasmFileChange={(file) => void loadCircuitFromFile(file)}
            />
          </div>
          {audioUrl ? (
            <audio
              ref={audioRef}
              src={audioUrl}
              onEnded={() => {
                stopPlaybackMonitor();
                setPlaybackTime(result?.duration ?? 0);
                setIsPlaying(false);
                setStatus("Ready");
              }}
              style={{ display: "none" }}
            />
          ) : null}
        </section>
      </div>
    </main>
  );
}
