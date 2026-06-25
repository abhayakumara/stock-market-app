"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const LINKS = [
  { href: "/", label: "Trade" },
  { href: "/analysis", label: "Analysis" },
  { href: "/backtest", label: "Backtest" },
  { href: "/live", label: "Live" },
  { href: "/coach", label: "Coach" },
];

export function Nav() {
  const pathname = usePathname();
  return (
    <nav className="topnav">
      <span className="brand">AI Trading</span>
      <div className="links">
        {LINKS.map((l) => (
          <Link
            key={l.href}
            href={l.href}
            className={pathname === l.href ? "active" : ""}
          >
            {l.label}
          </Link>
        ))}
      </div>
      <span className="badge">PAPER · Zerodha Kite</span>
    </nav>
  );
}
