"use client";

import { useCallback, useEffect, useState } from "react";
import { JournalEntry, api } from "@/lib/api";

export default function CoachPage() {
  const [coaching, setCoaching] = useState("");
  const [review, setReview] = useState("");
  const [entries, setEntries] = useState<JournalEntry[]>([]);
  const [note, setNote] = useState("");
  const [tags, setTags] = useState("");
  const [busy, setBusy] = useState<string>("");
  const [aiErr, setAiErr] = useState("");

  const loadJournal = useCallback(() => {
    api.journal().then((r) => setEntries(r.entries)).catch(() => {});
  }, []);

  useEffect(() => {
    loadJournal();
  }, [loadJournal]);

  async function getCoaching() {
    setBusy("coach");
    setAiErr("");
    try {
      setCoaching((await api.aiCoach()).coaching);
    } catch (e) {
      setAiErr(aiMessage(e));
    } finally {
      setBusy("");
    }
  }

  async function getReview() {
    setBusy("review");
    setAiErr("");
    try {
      setReview((await api.aiReview()).review);
    } catch (e) {
      setAiErr(aiMessage(e));
    } finally {
      setBusy("");
    }
  }

  async function addNote() {
    if (!note.trim()) return;
    await api.addJournal(
      note,
      tags.split(",").map((t) => t.trim()).filter(Boolean),
    );
    setNote("");
    setTags("");
    loadJournal();
  }

  return (
    <>
      <div className="grid">
        <div className="panel">
          <h2>AI trading coach</h2>
          <p className="muted">
            Educational feedback on your paper account: risk discipline, position sizing,
            and over-trading. Suggestions only — never auto-executed.
          </p>
          <button className="primary" disabled={busy === "coach"} onClick={getCoaching}>
            {busy === "coach" ? "Thinking…" : "Get coaching"}
          </button>
          {coaching && <p className="ai-text">{coaching}</p>}
        </div>

        <div className="panel">
          <h2>AI trade review</h2>
          <p className="muted">Auto-review of your recent trades for patterns and lessons.</p>
          <button className="primary" disabled={busy === "review"} onClick={getReview}>
            {busy === "review" ? "Reviewing…" : "Review my trades"}
          </button>
          {review && <p className="ai-text">{review}</p>}
        </div>
      </div>

      {aiErr && <div className="warn">{aiErr}</div>}

      <div className="panel">
        <h2>Trade journal</h2>
        <p className="muted">
          Writing down why you entered and exited is one of the highest-ROI habits in
          trading. Keep it honest.
        </p>
        <div className="journal-form">
          <textarea
            placeholder="What did you do and why? What would you change?"
            value={note}
            onChange={(e) => setNote(e.target.value)}
          />
          <input
            placeholder="tags (comma separated)"
            value={tags}
            onChange={(e) => setTags(e.target.value)}
          />
          <button className="primary" onClick={addNote}>
            Add entry
          </button>
        </div>
        {entries.length === 0 ? (
          <p className="muted">No journal entries yet.</p>
        ) : (
          <ul className="journal">
            {entries
              .slice()
              .reverse()
              .map((e) => (
                <li key={e.id}>
                  <div className="jmeta">
                    {new Date(e.created_at).toLocaleString()}{" "}
                    {e.tags.map((t) => (
                      <span key={t} className="tag">
                        {t}
                      </span>
                    ))}
                  </div>
                  <div>{e.text}</div>
                </li>
              ))}
          </ul>
        )}
      </div>

      <p className="disclaimer">Educational only — not investment advice.</p>
    </>
  );
}

function aiMessage(e: unknown): string {
  const m = e instanceof Error ? e.message : "AI unavailable";
  if (m.toLowerCase().includes("anthropic")) {
    return "Set ANTHROPIC_API_KEY (and install the AI extra) to enable Claude features.";
  }
  return m;
}
