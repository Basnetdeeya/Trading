"use client";

type Props = { strategies: any[]; onChange: () => void };

export default function StrategyTable({ strategies, onChange }: Props) {
  const toggle = async (name: string, enabled: boolean) => {
    await fetch("/api/v1/strategies/toggle", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, enabled }),
    });
    onChange();
  };

  return (
    <table>
      <thead>
        <tr>
          <th>Strategy</th>
          <th>Description</th>
          <th>Enabled</th>
        </tr>
      </thead>
      <tbody>
        {strategies.map((s) => (
          <tr key={s.name}>
            <td><code>{s.name}</code></td>
            <td style={{ color: "var(--muted)" }}>{s.description}</td>
            <td>
              <input type="checkbox" checked={s.enabled} onChange={(e) => toggle(s.name, e.target.checked)} />
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
