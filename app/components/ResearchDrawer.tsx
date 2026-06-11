"use client";

import { useEffect } from "react";

interface ResearchDrawerProps {
  open: boolean;
  onClose: () => void;
  metricsText: string;
  logs: string[];
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
        aria-hidden={!open}
        aria-label="Research panel"
      >
        <div className="research-drawer__header">
          <h2 className="research-drawer__title">Research</h2>
          <button
            type="button"
            className="research-drawer__close"
            onClick={onClose}
            aria-label="Close research panel"
          >
            ×
          </button>
        </div>
        <div className="research-drawer__body stack">
          <div className="card">
            <div className="card__head">
              <h3 className="card__title">Spectral analysis</h3>
              <span className="card__accent" />
            </div>
            <div className="metrics-box">{metricsText}</div>
          </div>
          <div className="card">
            <div className="card__head">
              <h3 className="card__title">Session log</h3>
              <span className="card__accent" />
            </div>
            <div className="log-box">{logs.join("\n") || "Your studio session log appears here."}</div>
          </div>
        </div>
      </aside>
    </>
  );
}
