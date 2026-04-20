"use client";
import { LineChart, Line, XAxis, YAxis, ResponsiveContainer, Tooltip, CartesianGrid } from "recharts";

export default function EquityChart({ portfolio }: { portfolio: any }) {
  const curve = (portfolio?.equity_curve || []) as { timestamp: string; equity: number }[];
  const data = curve.length
    ? curve.map((p, i) => ({ i, equity: p.equity }))
    : [{ i: 0, equity: portfolio.starting_capital }, { i: 1, equity: portfolio.equity }];
  return (
    <ResponsiveContainer width="100%" height={220}>
      <LineChart data={data}>
        <CartesianGrid strokeDasharray="3 3" stroke="#222a3a" />
        <XAxis dataKey="i" stroke="#8891a6" tick={{ fontSize: 11 }} />
        <YAxis stroke="#8891a6" tick={{ fontSize: 11 }} domain={["auto", "auto"]} />
        <Tooltip contentStyle={{ background: "#121722", border: "1px solid #222a3a" }} />
        <Line type="monotone" dataKey="equity" stroke="#57a7ff" strokeWidth={2} dot={false} />
      </LineChart>
    </ResponsiveContainer>
  );
}
