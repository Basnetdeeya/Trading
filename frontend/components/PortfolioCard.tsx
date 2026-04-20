type P = {
  portfolio: {
    equity: number; cash: number; starting_capital: number;
    return_pct: number; drawdown_pct: number; open_positions: any[]; closed_trades: number;
  };
};

export default function PortfolioCard({ portfolio }: P) {
  const r = portfolio.return_pct;
  return (
    <div className="grid grid-4">
      <div className="card">
        <h3>Equity</h3>
        <div className="kpi">${portfolio.equity.toLocaleString()}</div>
        <div className="kpi sub">start: ${portfolio.starting_capital.toLocaleString()}</div>
      </div>
      <div className="card">
        <h3>Return</h3>
        <div className={`kpi ${r >= 0 ? "pos" : "neg"}`}>{r.toFixed(2)}%</div>
        <div className="kpi sub">cash ${portfolio.cash.toLocaleString()}</div>
      </div>
      <div className="card">
        <h3>Drawdown</h3>
        <div className={`kpi ${portfolio.drawdown_pct > 10 ? "warn" : ""}`}>
          {portfolio.drawdown_pct.toFixed(2)}%
        </div>
        <div className="kpi sub">from peak</div>
      </div>
      <div className="card">
        <h3>Positions</h3>
        <div className="kpi">{portfolio.open_positions.length}</div>
        <div className="kpi sub">closed trades: {portfolio.closed_trades}</div>
      </div>
    </div>
  );
}
