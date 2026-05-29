import type { GenerateResult } from "@/lib/types";

const COLORS = {
  grid: "rgba(255, 255, 255, 0.04)",
  label: "#6b7694",
  waveform: "#c084fc",
  waveformGlow: "rgba(192, 132, 252, 0.4)",
  playback: "#f472b6",
  spectrum: "#22d3ee",
  spectrumFill: "rgba(34, 211, 238, 0.08)",
};

function drawGrid(ctx: CanvasRenderingContext2D, w: number, h: number) {
  ctx.strokeStyle = COLORS.grid;
  ctx.lineWidth = 1;
  for (let i = 1; i < 4; i += 1) {
    const y = (h / 4) * i;
    ctx.beginPath();
    ctx.moveTo(0, y);
    ctx.lineTo(w, y);
    ctx.stroke();
  }
}

export function drawWaveformPanel(
  timeCanvas: HTMLCanvasElement,
  spectrumCanvas: HTMLCanvasElement,
  result: GenerateResult | null,
  playbackTimeSec: number | null,
) {
  const timeCtx = timeCanvas.getContext("2d");
  const spectrumCtx = spectrumCanvas.getContext("2d");
  if (!timeCtx || !spectrumCtx) return;

  const timeRect = timeCanvas.getBoundingClientRect();
  const spectrumRect = spectrumCanvas.getBoundingClientRect();
  const dpr = window.devicePixelRatio || 1;

  for (const [canvas, rect, ctx] of [
    [timeCanvas, timeRect, timeCtx],
    [spectrumCanvas, spectrumRect, spectrumCtx],
  ] as const) {
    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, rect.width, rect.height);
    drawGrid(ctx, rect.width, rect.height);
  }

  if (!result?.waveform_preview?.length) {
    for (const [ctx, label] of [
      [timeCtx, "Waveform"],
      [spectrumCtx, "Spectrum"],
    ] as const) {
      ctx.fillStyle = COLORS.label;
      ctx.font = "600 11px DM Sans, sans-serif";
      ctx.fillText(label, 14, 22);
      ctx.font = "400 10px DM Sans, sans-serif";
      ctx.fillText("Generate audio to visualize", 14, 38);
    }
    return;
  }

  const duration = result.duration;
  const preview = result.waveform_preview;
  const tw = timeRect.width;
  const th = timeRect.height;
  const midY = th / 2;

  timeCtx.shadowColor = COLORS.waveformGlow;
  timeCtx.shadowBlur = 8;
  timeCtx.strokeStyle = COLORS.waveform;
  timeCtx.lineWidth = 1.5;
  timeCtx.beginPath();
  preview.forEach((value, index) => {
    const x = (index / Math.max(preview.length - 1, 1)) * tw;
    const y = midY - value * th * 0.4;
    if (index === 0) timeCtx.moveTo(x, y);
    else timeCtx.lineTo(x, y);
  });
  timeCtx.stroke();
  timeCtx.shadowBlur = 0;

  timeCtx.fillStyle = COLORS.label;
  timeCtx.font = "600 10px DM Sans, sans-serif";
  timeCtx.fillText("WAVEFORM", 14, 18);
  timeCtx.font = "400 9px DM Sans, sans-serif";
  timeCtx.fillText("Time (s)", tw / 2 - 18, th - 8);

  if (playbackTimeSec !== null && duration > 0) {
    const px = Math.max(0, Math.min(playbackTimeSec / duration, 1)) * tw;
    timeCtx.strokeStyle = COLORS.playback;
    timeCtx.shadowColor = "rgba(244, 114, 182, 0.6)";
    timeCtx.shadowBlur = 10;
    timeCtx.lineWidth = 2;
    timeCtx.beginPath();
    timeCtx.moveTo(px, 0);
    timeCtx.lineTo(px, th);
    timeCtx.stroke();
    timeCtx.shadowBlur = 0;
  }

  const spec = result.spectrum_preview;
  const sw = spectrumRect.width;
  const sh = spectrumRect.height;
  if (spec?.frequencies_hz?.length) {
    const freqs = spec.frequencies_hz;
    const mags = spec.magnitude_db;
    const maxDb = Math.max(...mags);
    const minDb = maxDb - 80;

    spectrumCtx.beginPath();
    freqs.forEach((freq, index) => {
      const x = (freq / Math.max(freqs[freqs.length - 1], 1)) * sw;
      const norm = (mags[index] - minDb) / Math.max(maxDb - minDb, 1);
      const y = sh - norm * (sh - 24) - 12;
      if (index === 0) spectrumCtx.moveTo(x, sh);
      spectrumCtx.lineTo(x, y);
    });
    spectrumCtx.lineTo(sw, sh);
    spectrumCtx.closePath();
    spectrumCtx.fillStyle = COLORS.spectrumFill;
    spectrumCtx.fill();

    spectrumCtx.shadowColor = "rgba(34, 211, 238, 0.5)";
    spectrumCtx.shadowBlur = 6;
    spectrumCtx.strokeStyle = COLORS.spectrum;
    spectrumCtx.lineWidth = 1.5;
    spectrumCtx.beginPath();
    freqs.forEach((freq, index) => {
      const x = (freq / Math.max(freqs[freqs.length - 1], 1)) * sw;
      const norm = (mags[index] - minDb) / Math.max(maxDb - minDb, 1);
      const y = sh - norm * (sh - 24) - 12;
      if (index === 0) spectrumCtx.moveTo(x, y);
      else spectrumCtx.lineTo(x, y);
    });
    spectrumCtx.stroke();
    spectrumCtx.shadowBlur = 0;
  }

  spectrumCtx.fillStyle = COLORS.label;
  spectrumCtx.font = "600 10px DM Sans, sans-serif";
  spectrumCtx.fillText("SPECTRUM", 14, 18);
  spectrumCtx.font = "400 9px DM Sans, sans-serif";
  spectrumCtx.fillText("Frequency (Hz)", sw / 2 - 36, sh - 8);
}
