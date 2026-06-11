"use client";

import type { ChangeEvent, RefObject } from "react";

interface AudioPlayerProps {
  disabled: boolean;
  isPlaying: boolean;
  playbackTime: number;
  duration: number;
  canSave: boolean;
  onPlayPause: () => void;
  onSeek: (time: number) => void;
  onSaveAudio: () => void;
  onLoadQasm: () => void;
  onExportCircuit: () => void;
  qasmInputRef: RefObject<HTMLInputElement>;
  onQasmFileChange: (file: File) => void;
}

function formatTime(seconds: number): string {
  if (!Number.isFinite(seconds) || seconds < 0) return "0:00";
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${secs.toString().padStart(2, "0")}`;
}

export function AudioPlayer({
  disabled,
  isPlaying,
  playbackTime,
  duration,
  canSave,
  onPlayPause,
  onSeek,
  onSaveAudio,
  onLoadQasm,
  onExportCircuit,
  qasmInputRef,
  onQasmFileChange,
}: AudioPlayerProps) {
  const safeDuration = duration > 0 ? duration : 0;
  const safePlayback = Math.min(Math.max(playbackTime, 0), safeDuration || 0);

  const handleSeek = (event: ChangeEvent<HTMLInputElement>) => {
    onSeek(Number(event.target.value));
  };

  return (
    <div className={`player-bar ${disabled ? "player-bar--disabled" : ""}`}>
      <div className="player-bar__transport">
        <button
          type="button"
          className="player-bar__play"
          onClick={onPlayPause}
          disabled={disabled}
          aria-label={isPlaying ? "Pause" : "Play"}
        >
          {isPlaying ? "⏸" : "▶"}
        </button>
        <input
          type="range"
          className="player-bar__seek"
          min={0}
          max={safeDuration || 0}
          step={0.01}
          value={safePlayback}
          onChange={handleSeek}
          disabled={disabled || safeDuration <= 0}
          aria-label="Seek"
        />
        <span className="player-bar__time">
          {formatTime(safePlayback)} / {formatTime(safeDuration)}
        </span>
      </div>
      <div className="player-bar__actions">
        <button
          type="button"
          className="btn-ghost"
          onClick={onSaveAudio}
          disabled={!canSave}
          title={canSave ? "Download the generated audio" : "Generate audio first"}
        >
          Save Audio
        </button>
        <button type="button" className="btn-ghost" onClick={onLoadQasm}>
          Load QASM
        </button>
        <button type="button" className="btn-ghost" onClick={onExportCircuit}>
          Export circuit
        </button>
        <input
          ref={qasmInputRef}
          type="file"
          accept=".qasm,text/plain"
          hidden
          onChange={(event) => {
            const file = event.target.files?.[0];
            if (file) onQasmFileChange(file);
            event.target.value = "";
          }}
        />
      </div>
    </div>
  );
}
