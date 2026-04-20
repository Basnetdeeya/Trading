"use client";
import { useState } from "react";

type Props = { risk: any; onUpdated: () => void };

export default function RiskControls({ risk, onUpdated }: Props) {
  const [maxPos, setMaxPos] = useState(risk?.limits?.max_position_pct ?? 0.05);
  const [maxDD, setMaxDD] = useState(risk?.limits?.max_drawdown_pct ?? 0.15);
  const [maxDaily, setMaxDaily] = useState(risk?.limits?.max_daily_loss_pct ?? 0.02);
  const [maxOpen, setMaxOpen] = useState(risk?.limits?.max_open_positions ?? 8);
  const [useKelly, setUseKelly] = useState(risk?.limits?.use_kelly ?? false);
  const [saving, setSaving] = useState(false);

  const save = async () => {
    setSaving(true);
    try {
      await fetch("/api/v1/risk", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          max_position_pct: maxPos,
          max_drawdown_pct: maxDD,
          max_daily_loss_pct: maxDaily,
          max_open_positions: Number(maxOpen),
          use_kelly: useKelly,
        }),
      });
      onUpdated();
    } finally {
      setSaving(false);
    }
  };

  return (
    <div>
      <div className="slider-row">
        <label>Max position %</label>
        <input type="range" min={0.01} max={0.5} step={0.005} value={maxPos} onChange={(e) => setMaxPos(parseFloat(e.target.value))} />
        <span>{(maxPos * 100).toFixed(1)}%</span>
      </div>
      <div className="slider-row">
        <label>Max drawdown %</label>
        <input type="range" min={0.02} max={0.5} step={0.005} value={maxDD} onChange={(e) => setMaxDD(parseFloat(e.target.value))} />
        <span>{(maxDD * 100).toFixed(1)}%</span>
      </div>
      <div className="slider-row">
        <label>Max daily loss %</label>
        <input type="range" min={0.005} max={0.1} step={0.005} value={maxDaily} onChange={(e) => setMaxDaily(parseFloat(e.target.value))} />
        <span>{(maxDaily * 100).toFixed(1)}%</span>
      </div>
      <div className="slider-row">
        <label>Max open positions</label>
        <input type="number" min={1} max={50} value={maxOpen} onChange={(e) => setMaxOpen(parseInt(e.target.value, 10))} style={{ width: 80 }} />
      </div>
      <div className="slider-row">
        <label>Half-Kelly sizing</label>
        <input type="checkbox" checked={useKelly} onChange={(e) => setUseKelly(e.target.checked)} />
      </div>
      <button className="primary" onClick={save} disabled={saving}>{saving ? "Saving…" : "Save risk settings"}</button>
    </div>
  );
}
