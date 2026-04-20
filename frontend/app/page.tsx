"use client";

import useSWR from "swr";
import { useState } from "react";
import PortfolioCard from "@/components/PortfolioCard";
import RiskControls from "@/components/RiskControls";
import StrategyTable from "@/components/StrategyTable";
import AIInsights from "@/components/AIInsights";
import TradesTable from "@/components/TradesTable";
import EquityChart from "@/components/EquityChart";
import BacktestPanel from "@/components/BacktestPanel";

const fetcher = (u: string) => fetch(u).then((r) => r.json());

export default function Dashboard() {
  const { data: dash, mutate } = useSWR("/api/v1/dashboard", fetcher, { refreshInterval: 10_000 });
  const { data: insights } = useSWR("/api/v1/insights", fetcher, { refreshInterval: 10_000 });
  const [ticking, setTicking] = useState(false);

  const runTick = async () => {
    setTicking(true);
    try {
      await fetch("/api/v1/engine/tick", { method: "POST" });
      await mutate();
    } finally {
      setTicking(false);
    }
  };

  const halt = async () => { await fetch("/api/v1/control/halt?reason=manual", { method: "POST" }); mutate(); };
  const resume = async () => { await fetch("/api/v1/control/resume", { method: "POST" }); mutate(); };

  if (!dash) return <p>Loading dashboard…</p>;

  const mode = dash.mode || "paper";
  const halted = dash?.risk?.halted;

  return (
    <div>
      <div className="disclaimer">
        This platform is for research and paper trading. No output constitutes
        investment advice. Predictions are probabilistic and may be wrong.
      </div>

      <div className="controls" style={{ marginBottom: 16 }}>
        <span className={`badge ${mode === "live" ? "live" : "paper"}`}>mode: {mode}</span>
        <span className="badge">broker: {dash.broker}</span>
        {halted ? <span className="badge sell">HALTED — {dash.risk.reason}</span> : <span className="badge buy">active</span>}
        <button className="primary" onClick={runTick} disabled={ticking}>
          {ticking ? "Running…" : "Run cycle"}
        </button>
        {halted ? <button onClick={resume}>Resume</button> : <button className="danger" onClick={halt}>Halt</button>}
      </div>

      <PortfolioCard portfolio={dash.portfolio} />

      <div className="grid grid-2" style={{ marginTop: 16 }}>
        <div className="card">
          <h3>Equity curve</h3>
          <EquityChart portfolio={dash.portfolio} />
        </div>
        <div className="card">
          <h3>AI insights</h3>
          <AIInsights decisions={insights?.decisions || {}} />
        </div>
      </div>

      <div className="grid grid-2" style={{ marginTop: 16 }}>
        <div className="card">
          <h3>Risk controls</h3>
          <RiskControls risk={dash.risk} onUpdated={mutate} />
        </div>
        <div className="card">
          <h3>Recent fills</h3>
          <TradesTable trades={dash.recent_fills || []} />
        </div>
      </div>

      <div className="card" style={{ marginTop: 16 }}>
        <h3>Strategies</h3>
        <StrategyTable strategies={dash.strategies || []} onChange={mutate} />
      </div>

      <div className="card" style={{ marginTop: 16 }}>
        <h3>Backtest</h3>
        <BacktestPanel />
      </div>
    </div>
  );
}
