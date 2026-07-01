"use client";

import Link from "next/link";

/**
 * The four-stage path every strategy should travel before it ever risks a rupee:
 * learn it, prove it on history, prove it on live paper money, then (only then)
 * promote it to real money behind the risk gate. Shown across pages so the user
 * always knows where they are and what the professional next step is.
 */
export interface JourneyStep {
  key: string;
  href: string;
  label: string;
  hint: string;
  icon: string;
}

export const JOURNEY_STEPS: JourneyStep[] = [
  { key: "learn", href: "/analysis", label: "Learn", hint: "Read the chart & the idea", icon: "📚" },
  { key: "backtest", href: "/backtest", label: "Backtest", hint: "Prove it on past data", icon: "🧪" },
  { key: "paper", href: "/", label: "Paper trade", hint: "Prove it with fake money, live", icon: "📝" },
  { key: "real", href: "/live", label: "Real money", hint: "Promote behind the risk gate", icon: "💰" },
];

export function Journey({ active }: { active: string }) {
  const activeIdx = JOURNEY_STEPS.findIndex((s) => s.key === active);
  return (
    <div className="journey" aria-label="Your trading journey">
      {JOURNEY_STEPS.map((s, i) => {
        const state = i < activeIdx ? "past" : i === activeIdx ? "current" : "future";
        return (
          <Link key={s.key} href={s.href} className={`jstep ${state}`}>
            <span className="jicon">{s.icon}</span>
            <span className="jbody">
              <span className="jlabel">
                <span className="jnum">{i + 1}</span>
                {s.label}
              </span>
              <span className="jhint">{s.hint}</span>
            </span>
          </Link>
        );
      })}
    </div>
  );
}
