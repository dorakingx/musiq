import type { GenerateResult } from "@/lib/types";

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
  }

  if (!result?.waveform_preview?.length) {
    timeCtx.fillStyle = "#888";
    timeCtx.font = "12px sans-serif";
    timeCtx.fillText("Waveform", 8, 16);
    spectrumCtx.fillStyle = "#888";
    spectrumCtx.fillText("Magnitude Spectrum", 8, 16);
    return;
  }

  const duration = result.duration;
  const preview = result.waveform_preview;
  const tw = timeRect.width;
  const th = timeRect.height;

  timeCtx.strokeStyle = "#1565c0";
  timeCtx.lineWidth = 1;
  timeCtx.beginPath();
  preview.forEach((value, index) => {
    const x = (index / Math.max(preview.length - 1, 1)) * tw;
    const y = th / 2 - value * th * 0.42;
    if (index === 0) timeCtx.moveTo(x, y);
    else timeCtx.lineTo(x, y);
  });
  timeCtx.stroke();
  timeCtx.fillStyle = "#333";
  timeCtx.font = "11px sans-serif";
  timeCtx.fillText("Waveform", 8, 14);
  timeCtx.fillText("Time (s)", tw / 2 - 20, th - 4);

  if (playbackTimeSec !== null && duration > 0) {
    const px = Math.max(0, Math.min(playbackTimeSec / duration, 1)) * tw;
    timeCtx.strokeStyle = "#e53935";
    timeCtx.lineWidth = 1.5;
    timeCtx.beginPath();
    timeCtx.moveTo(px, 0);
    timeCtx.lineTo(px, th);
    timeCtx.stroke();
  }

  const spec = result.spectrum_preview;
  const sw = spectrumRect.width;
  const sh = spectrumRect.height;
  if (spec?.frequencies_hz?.length) {
    const freqs = spec.frequencies_hz;
    const mags = spec.magnitude_db;
    const maxDb = Math.max(...mags);
    const minDb = maxDb - 80;
    spectrumCtx.strokeStyle = "#ff7043";
    spectrumCtx.lineWidth = 1;
    spectrumCtx.beginPath();
    freqs.forEach((freq, index) => {
      const x = (freq / Math.max(freqs[freqs.length - 1], 1)) * sw;
      const norm = (mags[index] - minDb) / Math.max(maxDb - minDb, 1);
      const y = sh - norm * (sh - 20) - 8;
      if (index === 0) spectrumCtx.moveTo(x, y);
      else spectrumCtx.lineTo(x, y);
    });
    spectrumCtx.stroke();
  }
  spectrumCtx.fillStyle = "#333";
  spectrumCtx.font = "11px sans-serif";
  spectrumCtx.fillText("Magnitude Spectrum", 8, 14);
  spectrumCtx.fillText("Frequency (Hz)", sw / 2 - 36, sh - 4);
}
