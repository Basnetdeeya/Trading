export default function TradesTable({ trades }: { trades: any[] }) {
  if (!trades.length) return <p style={{ color: "var(--muted)" }}>No fills yet.</p>;
  return (
    <table>
      <thead>
        <tr>
          <th>Time</th><th>Symbol</th><th>Side</th><th>Qty</th><th>Price</th><th>PnL</th><th>Strategy</th>
        </tr>
      </thead>
      <tbody>
        {trades.slice().reverse().map((t, i) => (
          <tr key={i}>
            <td style={{ color: "var(--muted)" }}>{new Date(t.timestamp).toLocaleTimeString()}</td>
            <td><strong>{t.symbol}</strong></td>
            <td><span className={`badge ${t.side === "BUY" ? "buy" : "sell"}`}>{t.side}</span></td>
            <td>{Number(t.qty).toFixed(4)}</td>
            <td>${Number(t.price).toFixed(2)}</td>
            <td className={t.pnl > 0 ? "pos" : t.pnl < 0 ? "neg" : ""}>
              {t.pnl == null ? "—" : `$${Number(t.pnl).toFixed(2)}`}
            </td>
            <td><code>{t.strategy}</code></td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
