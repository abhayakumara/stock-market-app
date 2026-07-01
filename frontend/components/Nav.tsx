"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const LINKS = [
  { href: "/", label: "Trade", icon: "💹" },
  { href: "/analysis", label: "Analysis", icon: "📈" },
  { href: "/backtest", label: "Strategies", icon: "🧪" },
  { href: "/live", label: "Live", icon: "💰" },
  { href: "/coach", label: "Coach", icon: "🧠" },
];

export function Nav() {
  const pathname = usePathname();
  return (
    <nav className="topnav">
      <Link href="/" className="brand">
        <span className="brand-mark">▲</span> AlphaDesk
      </Link>
      <div className="links">
        {LINKS.map((l) => (
          <Link
            key={l.href}
            href={l.href}
            className={pathname === l.href ? "active" : ""}
          >
            <span className="nav-ico" aria-hidden>{l.icon}</span>
            {l.label}
          </Link>
        ))}
      </div>
      <span className="badge safe" title="You are trading virtual money. No real orders are placed here.">
        ● PAPER MONEY
      </span>
    </nav>
  );
}
