import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Quant Sentinel",
  description: "Multi-asset automated trading dashboard (paper-first)",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <header className="topbar">
          <div className="logo">Quant&nbsp;Sentinel</div>
          <div className="tagline">paper-first multi-asset trading</div>
        </header>
        <main>{children}</main>
        <footer className="footer">
          Trading involves risk of loss. Not financial advice.
        </footer>
      </body>
    </html>
  );
}
