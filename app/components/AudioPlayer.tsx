"use client";

import type { ChangeEvent, CSSProperties } from "react";
import { DownloadIcon, PauseIcon, PlayIcon, StopIcon } from "@/app/components/PlayerIcons";

interface AudioPlayerProps {
  disabled: boolean;
  isPlaying: boolean;
  playbackTime: number;
  duration: number;
  canSave: boolean;
  onPlayPause: () => void;
  onStop: () => void;
  onSeek: (time: number) => void;
  onSaveAudio: () => void;
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
  onStop,
  onSeek,
  onSaveAudio,
}: AudioPlayerProps) {
  const safeDuration = duration > 0 ? duration : 0;
  const safePlayback = Math.min(Math.max(playbackTime, 0), safeDuration || 0);
  const seekProgress = safeDuration > 0 ? (safePlayback / safeDuration) * 100 : 0;

  const handleSeek = (event: ChangeEvent<HTMLInputElement>) => {
    onSeek(Number(event.target.value));
  };

  const seekStyle = {
    "--seek-progress": `${seekProgress}%`,
  } as CSSProperties;

  return (
    <div className={`player-card ${disabled ? "player-card--disabled" : ""}`}>
      <div className="player-card__controls">
        <div className="player-card__buttons">
          <button
            type="button"
            className="player-btn player-btn--primary"
            onClick={onPlayPause}
            disabled={disabled}
            aria-label={isPlaying ? "Pause" : "Play"}
          >
            {isPlaying ? <PauseIcon /> : <PlayIcon />}
          </button>
          <button
            type="button"
            className="player-btn"
            onClick={onStop}
            disabled={disabled}
            aria-label="Stop"
          >
            <StopIcon />
          </button>
        </div>

        <input
          type="range"
          className="player-card__seek"
          style={seekStyle}
          min={0}
          max={safeDuration || 0}
          step={0.01}
          value={safePlayback}
          onChange={handleSeek}
          disabled={disabled || safeDuration <= 0}
          aria-label="Seek"
        />

        <span className="player-card__time text-mono-muted">
          {formatTime(safePlayback)} / {formatTime(safeDuration)}
        </span>

        <button
          type="button"
          className="player-btn player-btn--save"
          onClick={onSaveAudio}
          disabled={!canSave}
          aria-label="Save Audio"
          title={canSave ? "Download the generated audio" : "Generate audio first"}
        >
          <DownloadIcon />
        </button>
      </div>
    </div>
  );
}
