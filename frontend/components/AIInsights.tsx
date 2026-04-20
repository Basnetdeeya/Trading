export default function AIInsights({ decisions }: { decisions: Record<string, any> }) {
  const entries = Object.entries(decisions || {});
  if (!entries.length) return <p style={{ color: "var(--muted)" }}>Waiting for the first engine cycle…</p>;
  return (
    <div>
      {entries.map(([symbol, d]) => (
        <div key={symbol} className="insight">
          <div className="label">{symbol} — regime: {d.regime}</div>
          <div>
            <span className={`badge ${d.side === "BUY" ? "buy" : d.side === "SELL" ? "sell" : "hold"}`}>{d.side}</span>{" "}
            <strong>{(d.confidence * 100).toFixed(0)}%</strong> via <code>{d.chosen_strategy || "—"}</code>
          </div>
          <div style={{ color: "var(--muted)", marginTop: 4 }}>{d.rationale}</div>
        </div>
      ))}
    </div>
  );
}
