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
import { drawWaveformPanel } from "@/lib/waveformPlot";

const COLUMN_WIDTH = 70;
const QUBIT_SPACING = 56;
const LEFT_MARGIN = 50;
const TOP_MARGIN = 30;

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
  const [playbackTime, setPlaybackTime] = useState<number | null>(null);
  const timeCanvasRef = useRef<HTMLCanvasElement | null>(null);
  const spectrumCanvasRef = useRef<HTMLCanvasElement | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const qasmInputRef = useRef<HTMLInputElement | null>(null);
  const generationIdRef = useRef(0);
  const abortRef = useRef<AbortController | null>(null);
  const playbackFrameRef = useRef<number | null>(null);

  const maxColumn = useMemo(() => {
    if (gates.length === 0) return 4;
    return Math.max(4, ...gates.map((gate) => gate.column + 1));
  }, [gates]);

  const gridColumns = Math.max(maxColumn + 4, 16);
  const svgWidth = LEFT_MARGIN + gridColumns * COLUMN_WIDTH + 40;
  const svgHeight = TOP_MARGIN + numQubits * QUBIT_SPACING + 24;

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

  const stopPlaybackMonitor = () => {
    if (playbackFrameRef.current !== null) {
      cancelAnimationFrame(playbackFrameRef.current);
      playbackFrameRef.current = null;
    }
  };

  const stopAudio = () => {
    const audio = audioRef.current;
    if (audio) {
      audio.pause();
      audio.currentTime = 0;
    }
    stopPlaybackMonitor();
    setPlaybackTime(result?.duration ?? null);
    appendLog("Audio stopped");
    setStatus("Ready");
  };

  const playAudio = () => {
    if (!audioUrl) {
      window.alert("Please generate audio first.");
      return;
    }
    const audio = audioRef.current;
    if (!audio) return;

    audio.currentTime = 0;
    setPlaybackTime(0);
    void audio.play();
    appendLog("Playing audio...");
    setStatus("Playing audio...");

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

  const clearCircuit = () => {
    setGates([]);
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
    if (gates.length === 0) {
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
    appendLog("Starting generation...");

    try {
      const response = await fetch("/api/generate_audio", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          num_qubits: numQubits,
          gates: gatesToPayload(gates),
          duration,
          sample_rate: sampleRate,
          shots,
          backend,
        }),
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

      downloadBlob(blob, nextResult.saved_audio_filename);
      appendLog(`Audio saved to: ${nextResult.saved_audio_filename}`);

      requestAnimationFrame(() => {
        const canvas = timeCanvasRef.current;
        if (!canvas) return;
        canvas.toBlob((pngBlob) => {
          if (!pngBlob) return;
          const pngName = nextResult.saved_audio_filename.replace(".wav", ".png");
          downloadBlob(pngBlob, pngName);
          appendLog(`Waveform PNG saved to: ${pngName}`);
        }, "image/png");
      });

      setPlaybackTime(null);
      setStatus("Audio generated successfully!");
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
      const response = await fetch("/api/circuit", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "import", qasm }),
      });
      const payload = await response.json();
      if (!response.ok || !payload.ok) {
        throw new Error(payload.error || "Import failed.");
      }
      setNumQubits(payload.num_qubits);
      setGates(payload.gates);
      appendLog(`Circuit loaded from: ${file.name}`);
      appendLog("Visual reconstruction complete.");
      window.alert(`Circuit successfully loaded and reconstructed from:\n${file.name}`);
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
      <header className="app-title">
        <img src="/musiq_logo.png" alt="Musiq logo" width={40} height={40} />
        <h1>Q-Wave: Quantum Circuit Audio Generator</h1>
      </header>

      <div className="grid">
        <section className="panel stack left-panel">
          <fieldset className="fieldset">
            <legend>Quantum Gates</legend>
            <div className="radio-list gate-radios">
              {GATE_OPTIONS.map((gate) => (
                <label key={gate.type} className="radio-item">
                  <input
                    type="radio"
                    name="gate"
                    value={gate.type}
                    checked={selectedGate === gate.type}
                    onChange={() => onGateSelected(gate.type)}
                  />
                  <span>{gate.label}</span>
                </label>
              ))}
            </div>
            <button className="secondary-btn" type="button" onClick={clearCircuit}>
              Clear Circuit
            </button>
          </fieldset>

          <fieldset className="fieldset">
            <legend>Circuit Parameters</legend>
            <div className="field">
              <label htmlFor="num-qubits">Number of Qubits:</label>
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
          </fieldset>

          <fieldset className="fieldset">
            <legend>Compute Resource</legend>
            <div className="radio-list">
              {BACKEND_OPTIONS.map((option) => (
                <label key={option.value} className="radio-item">
                  <input
                    type="radio"
                    name="backend"
                    value={option.value}
                    checked={backend === option.value}
                    onChange={() => handleBackendChange(option.value)}
                  />
                  <span>{option.label}</span>
                </label>
              ))}
            </div>
          </fieldset>

          <fieldset className="fieldset">
            <legend>Audio Parameters</legend>
            <div className="field">
              <label htmlFor="duration">Duration (seconds):</label>
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
              <label htmlFor="sample-rate">Sample Rate (Hz):</label>
              <select
                id="sample-rate"
                value={sampleRate}
                onChange={(event) => setSampleRate(Number(event.target.value))}
              >
                {SAMPLE_RATES.map((rate) => (
                  <option key={rate} value={rate}>
                    {rate}
                  </option>
                ))}
              </select>
            </div>
            <div className="field">
              <label htmlFor="shots">Measurement Shots:</label>
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
          </fieldset>

          <div className="control-buttons">
            <button
              className="primary-btn"
              type="button"
              disabled={isGenerating}
              onClick={generateAudio}
            >
              {isGenerating ? "Generating..." : "Generate Audio"}
            </button>
            <button className="secondary-btn" type="button" onClick={playAudio}>
              Play Audio
            </button>
            <button className="secondary-btn" type="button" onClick={stopAudio}>
              Stop Audio
            </button>
            <button className="secondary-btn" type="button" onClick={saveAudio}>
              Save Audio
            </button>
            <button
              className="secondary-btn"
              type="button"
              onClick={() => qasmInputRef.current?.click()}
            >
              Load Circuit
            </button>
            <button className="secondary-btn" type="button" onClick={saveCircuit}>
              Save Circuit
            </button>
            <input
              ref={qasmInputRef}
              type="file"
              accept=".qasm,text/plain"
              hidden
              onChange={(event) => {
                const file = event.target.files?.[0];
                if (file) void loadCircuitFromFile(file);
                event.target.value = "";
              }}
            />
          </div>

          {audioUrl ? (
            <audio
              ref={audioRef}
              src={audioUrl}
              onEnded={() => {
                stopPlaybackMonitor();
                setPlaybackTime(result?.duration ?? null);
                setStatus("Ready");
              }}
              style={{ display: "none" }}
            />
          ) : null}
        </section>

        <section className="panel stack center-panel">
          <h2 className="section-label">Quantum Circuit Builder</h2>
          <p className="hint">Click to place the selected gate. Click again on the same gate to remove.</p>
          <div className="circuit-board circuit-board-light">
            <svg
              className="circuit-svg"
              width={svgWidth}
              height={svgHeight}
              onClick={handleCircuitClick}
              onMouseMove={handleCircuitMove}
              onMouseLeave={() => setHoverCell(null)}
            >
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
                      stroke={col % 2 === 0 ? "#e0e0e0" : "#f0f0f0"}
                      strokeWidth={1}
                      strokeDasharray="2 4"
                    />
                    {col % 2 === 0 ? (
                      <text x={x} y={12} fill="#555" fontSize="8" textAnchor="middle">
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
                    <text x={10} y={y + 4} fill="#333" fontSize="12">{`q[${qubit}]`}</text>
                    <line
                      x1={LEFT_MARGIN}
                      y1={y}
                      x2={svgWidth - 20}
                      y2={y}
                      stroke="#888"
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
                      <line x1={x} y1={controlY} x2={x} y2={targetY} stroke={color} strokeWidth={2} />
                      <circle cx={x} cy={controlY} r={8} fill="white" stroke={color} strokeWidth={2} />
                      <circle cx={x} cy={targetY} r={8} fill="white" stroke={color} strokeWidth={2} />
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
                      rx={4}
                      fill="white"
                      stroke={color}
                      strokeWidth={2}
                    />
                    <text x={x} y={y + 5} textAnchor="middle" fill={color} fontSize="13" fontWeight="700">
                      {gate.type}
                    </text>
                  </g>
                );
              })}
            </svg>
          </div>

          <fieldset className="fieldset waveform-fieldset">
            <legend>Waveform</legend>
            <div className="waveform-stack">
              <div className="waveform-box waveform-box-light">
                <canvas ref={timeCanvasRef} className="waveform-canvas" />
              </div>
              <div className="waveform-box waveform-box-light">
                <canvas ref={spectrumCanvasRef} className="waveform-canvas" />
              </div>
            </div>
          </fieldset>
        </section>

        <section className="panel stack right-panel">
          <fieldset className="fieldset">
            <legend>Spectral Analysis Metrics</legend>
            <div className="metrics-box">{metricsText}</div>
          </fieldset>
          <fieldset className="fieldset">
            <legend>Log</legend>
            <div className="log-box">{logs.join("\n") || "Logs will appear here."}</div>
          </fieldset>
        </section>
      </div>

      <div className="status-bar status-bar-sunken">{status}</div>
    </main>
  );
}
