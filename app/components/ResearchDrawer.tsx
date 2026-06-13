"use client";

import { useEffect } from "react";
import { CloseIcon } from "@/app/components/PlayerIcons";

interface ResearchDrawerProps {
  open: boolean;
  onClose: () => void;
  metricsText: string;
  logs: string[];
}

function parseLogLine(line: string): { time: string | null; message: string } {
  const match = line.match(/^\[(\d{2}:\d{2}:\d{2})]\s*(.*)$/);
  if (match) {
    return { time: match[1], message: match[2] };
  }
  return { time: null, message: line };
}

export function ResearchDrawer({ open, onClose, metricsText, logs }: ResearchDrawerProps) {
  useEffect(() => {
    if (!open) return;

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };

    document.addEventListener("keydown", onKeyDown);
    document.body.style.overflow = "hidden";

    return () => {
      document.removeEventListener("keydown", onKeyDown);
      document.body.style.overflow = "";
    };
  }, [open, onClose]);

  return (
    <>
      <div
        className={`research-backdrop ${open ? "research-backdrop--visible" : ""}`}
        onClick={onClose}
        aria-hidden={!open}
      />
      <aside
        id="research-drawer"
        className={`research-drawer ${open ? "research-drawer--open" : ""}`}
        role="dialog"
        aria-modal={open}
        aria-hidden={!open}
        aria-label="Research panel"
      >
        <div className="research-drawer__header">
          <div>
            <h2 className="research-drawer__title">Research</h2>
            <p className="research-drawer__subtitle">Spectral analysis &amp; session log</p>
          </div>
          <button
            type="button"
            className="player-btn research-drawer__close"
            onClick={onClose}
            aria-label="Close research panel"
          >
            <CloseIcon />
          </button>
        </div>
        <div className="research-drawer__body stack">
          <div className="card card--drawer">
            <div className="card__head">
              <h3 className="card__title text-card-label">Spectral analysis</h3>
              <span className="card__accent" />
            </div>
            <div className="metrics-box">{metricsText}</div>
          </div>
          <div className="card card--drawer">
            <div className="card__head">
              <h3 className="card__title text-card-label">Session log</h3>
              <span className="card__accent" />
            </div>
            <div className="log-box">
              {logs.length === 0 ? (
                <p className="log-box__empty">Your studio session log appears here.</p>
              ) : (
                <ul className="log-list">
                  {logs.map((line, index) => {
                    const { time, message } = parseLogLine(line);
                    return (
                      <li key={`${index}-${line}`} className="log-line">
                        {time ? <span className="log-line__time">{time}</span> : null}
                        <span className="log-line__message">{message}</span>
                      </li>
                    );
                  })}
                </ul>
              )}
            </div>
          </div>
        </div>
      </aside>
    </>
  );
}
