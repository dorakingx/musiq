"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import {
  BACKEND_OPTIONS,
  GATE_COLORS,
  GATE_OPTIONS,
  type CircuitGate,
  type GateType,
  type GenerateResult,
} from "@/lib/types";

const COLUMN_WIDTH = 70;
const QUBIT_SPACING = 56;
const LEFT_MARGIN = 48;
const TOP_MARGIN = 32;

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
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const generationIdRef = useRef(0);

  const maxColumn = useMemo(() => {
    if (gates.length === 0) return 4;
    return Math.max(4, ...gates.map((gate) => gate.column + 1));
  }, [gates]);

  const svgWidth = LEFT_MARGIN + maxColumn * COLUMN_WIDTH + 40;
  const svgHeight = TOP_MARGIN + numQubits * QUBIT_SPACING + 24;

  useEffect(() => {
    return () => {
      if (audioUrl) URL.revokeObjectURL(audioUrl);
    };
  }, [audioUrl]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !result?.waveform_preview?.length) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const { width, height } = canvas.getBoundingClientRect();
    canvas.width = width * devicePixelRatio;
    canvas.height = height * devicePixelRatio;
    ctx.scale(devicePixelRatio, devicePixelRatio);
    ctx.clearRect(0, 0, width, height);

    const data = result.waveform_preview;
    ctx.strokeStyle = "#7c5cff";
    ctx.lineWidth = 2;
    ctx.beginPath();
    data.forEach((value, index) => {
      const x = (index / Math.max(data.length - 1, 1)) * width;
      const y = height / 2 - value * (height * 0.42);
      if (index === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    });
    ctx.stroke();
  }, [result]);

  const appendLog = (message: string) => {
    setLogs((prev) => [...prev, message]);
  };

  const clearCircuit = () => {
    setGates([]);
    appendLog("Circuit cleared.");
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
  };

  const handleCanvasClick = (event: React.MouseEvent<SVGSVGElement>) => {
    const rect = event.currentTarget.getBoundingClientRect();
    const x = event.clientX - rect.left - LEFT_MARGIN;
    const y = event.clientY - rect.top - TOP_MARGIN;
    if (x < 0 || y < 0) return;

    const column = Math.floor(x / COLUMN_WIDTH);
    const qubit = Math.floor(y / QUBIT_SPACING);
    if (qubit < 0 || qubit >= numQubits || column < 0) return;

    if (event.shiftKey) {
      removeGateAt(column, qubit);
      appendLog(`Removed gate at q${qubit}, column ${column}.`);
      return;
    }

    placeGate(column, qubit);
    appendLog(`Placed ${selectedGate} on q${qubit}, column ${column}.`);
  };

  const generateAudio = async () => {
    generationIdRef.current += 1;
    const generationId = generationIdRef.current;
    setIsGenerating(true);
    setStatus("Generating audio...");
    setLogs([]);
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

      setStatus("Audio generated successfully!");
      appendLog("Audio ready for playback.");
    } catch (error) {
      if (generationId !== generationIdRef.current) return;
      const message = error instanceof Error ? error.message : "Unknown error";
      setStatus("Generation failed");
      appendLog(`Error: ${message}`);
    } finally {
      if (generationId === generationIdRef.current) {
        setIsGenerating(false);
      }
    }
  };

  const metricsText = result
    ? Object.entries(result.analysis)
        .map(([key, value]) => `${key}: ${Number(value).toFixed(4)}`)
        .join("\n")
    : "Metrics will appear here after generation.";

  return (
    <main className="app-shell">
      <header className="hero">
        <img src="/musiq_logo.png" alt="Musiq logo" />
        <div>
          <h1>Musiq</h1>
          <p>Build quantum circuits in the browser and generate non-classical audio.</p>
        </div>
      </header>

      <div className="grid">
        <section className="panel stack">
          <div>
            <h2>Gates</h2>
            <div className="gate-grid">
              {GATE_OPTIONS.map((gate) => (
                <button
                  key={gate.type}
                  className={`gate-btn ${selectedGate === gate.type ? "active" : ""}`}
                  onClick={() => setSelectedGate(gate.type)}
                  type="button"
                >
                  {gate.label}
                </button>
              ))}
            </div>
          </div>

          <div className="field">
            <label htmlFor="num-qubits">Number of qubits</label>
            <input
              id="num-qubits"
              type="number"
              min={2}
              max={8}
              value={numQubits}
              onChange={(event) => {
                const value = Number(event.target.value);
                setNumQubits(value);
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

          <div>
            <h2>Compute Resource</h2>
            <div className="radio-list">
              {BACKEND_OPTIONS.map((option) => (
                <label key={option.value} className="radio-item">
                  <input
                    type="radio"
                    name="backend"
                    value={option.value}
                    checked={backend === option.value}
                    onChange={() => setBackend(option.value)}
                  />
                  <span>{option.label}</span>
                </label>
              ))}
            </div>
          </div>

          <div className="field">
            <label htmlFor="duration">Duration (seconds)</label>
            <input
              id="duration"
              type="number"
              min={0.5}
              max={30}
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
              {[22050, 44100, 48000].map((rate) => (
                <option key={rate} value={rate}>
                  {rate} Hz
                </option>
              ))}
            </select>
          </div>

          <div className="field">
            <label htmlFor="shots">Measurement shots</label>
            <input
              id="shots"
              type="number"
              min={128}
              max={8192}
              step={128}
              value={shots}
              onChange={(event) => setShots(Number(event.target.value))}
            />
          </div>

          <button className="primary-btn" type="button" disabled={isGenerating} onClick={generateAudio}>
            {isGenerating ? "Generating..." : "Generate Audio"}
          </button>
          <button className="secondary-btn" type="button" onClick={clearCircuit}>
            Clear Circuit
          </button>
          {audioUrl ? (
            <audio controls src={audioUrl} style={{ width: "100%" }}>
              Your browser does not support audio playback.
            </audio>
          ) : null}
        </section>

        <section className="panel stack">
          <div>
            <h2>Circuit Builder</h2>
            <p style={{ color: "var(--muted)", marginTop: 0 }}>
              Click to place the selected gate. Shift+click to remove.
            </p>
            <div className="circuit-board">
              <svg
                className="circuit-svg"
                width={svgWidth}
                height={svgHeight}
                onClick={handleCanvasClick}
              >
                {Array.from({ length: numQubits }).map((_, qubit) => {
                  const y = TOP_MARGIN + qubit * QUBIT_SPACING + QUBIT_SPACING / 2;
                  return (
                    <g key={`qubit-${qubit}`}>
                      <text x={8} y={y + 4} fill="#9fb0d0" fontSize="12">{`q${qubit}`}</text>
                      <line
                        x1={LEFT_MARGIN}
                        y1={y}
                        x2={svgWidth - 20}
                        y2={y}
                        stroke="#24304f"
                        strokeWidth={2}
                      />
                    </g>
                  );
                })}

                {gates.map((gate, index) => {
                  const x = LEFT_MARGIN + gate.column * COLUMN_WIDTH + COLUMN_WIDTH / 2;
                  if ("control" in gate) {
                    const controlY = TOP_MARGIN + gate.control * QUBIT_SPACING + QUBIT_SPACING / 2;
                    const targetY = TOP_MARGIN + gate.target * QUBIT_SPACING + QUBIT_SPACING / 2;
                    const color = GATE_COLORS[gate.type];
                    return (
                      <g key={`${gate.type}-${gate.column}-${index}`}>
                        <line x1={x} y1={controlY} x2={x} y2={targetY} stroke={color} strokeWidth={2} />
                        <circle cx={x} cy={controlY} r={7} fill={color} />
                        <circle cx={x} cy={targetY} r={7} fill={color} />
                        <text x={x + 10} y={targetY + 4} fill={color} fontSize="11">
                          {gate.type}
                        </text>
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
                        rx={8}
                        fill="rgba(255,255,255,0.04)"
                        stroke={color}
                        strokeWidth={2}
                      />
                      <text x={x} y={y + 4} textAnchor="middle" fill={color} fontSize="13" fontWeight="700">
                        {gate.type}
                      </text>
                    </g>
                  );
                })}
              </svg>
            </div>
          </div>

          <div>
            <h2>Waveform</h2>
            <div className="waveform-box">
              <canvas ref={canvasRef} className="waveform-canvas" />
            </div>
          </div>
        </section>

        <section className="panel stack">
          <div>
            <h2>Metrics</h2>
            <div className="metrics-box">{metricsText}</div>
          </div>
          <div>
            <h2>Log</h2>
            <div className="log-box">{logs.join("\n") || "Logs will appear here."}</div>
          </div>
        </section>
      </div>

      <div className="status-bar">{status}</div>
    </main>
  );
}
