"use client";
import { useState } from "react";

export default function BacktestPanel() {
  const [symbol, setSymbol] = useState("BTC-USD");
  const [asset, setAsset] = useState("crypto");
  const [interval, setInterval] = useState("1h");
  const [running, setRunning] = useState(false);
  const [results, setResults] = useState<any[]>([]);

  const run = async () => {
    setRunning(true);
    try {
      const res = await fetch("/api/v1/backtest", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ symbol, asset_class: asset, interval, lookback: 500 }),
      });
      const data = await res.json();
      setResults(data.results || []);
    } finally {
      setRunning(false);
    }
  };

  return (
    <div>
      <div className="controls" style={{ marginBottom: 12 }}>
        <input type="text" value={symbol} onChange={(e) => setSymbol(e.target.value)} />
        <select value={asset} onChange={(e) => setAsset(e.target.value)}>
          <option value="crypto">crypto</option>
          <option value="equity">equity</option>
          <option value="forex">forex</option>
          <option value="prediction">prediction</option>
        </select>
        <select value={interval} onChange={(e) => setInterval(e.target.value)}>
          <option>15m</option><option>1h</option><option>4h</option><option>1d</option>
        </select>
        <button className="primary" onClick={run} disabled={running}>{running ? "Running…" : "Run backtest"}</button>
      </div>
      {results.length > 0 && (
        <table>
          <thead>
            <tr>
              <th>Strategy</th><th>Return</th><th>Sharpe</th><th>Max DD</th><th>Win %</th><th>PF</th><th>Trades</th>
            </tr>
          </thead>
          <tbody>
            {results.map((r) => (
              <tr key={r.strategy}>
                <td><code>{r.strategy}</code></td>
                <td className={r.metrics.total_return >= 0 ? "pos" : "neg"}>
                  {(r.metrics.total_return * 100).toFixed(2)}%
                </td>
                <td>{r.metrics.sharpe.toFixed(2)}</td>
                <td className="warn">{(r.metrics.max_drawdown * 100).toFixed(2)}%</td>
                <td>{(r.metrics.win_rate * 100).toFixed(1)}%</td>
                <td>{r.metrics.profit_factor.toFixed(2)}</td>
                <td>{r.metrics.trades}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
