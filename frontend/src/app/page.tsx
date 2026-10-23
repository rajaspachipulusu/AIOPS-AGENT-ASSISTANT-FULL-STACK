"use client";

import { useEffect, useRef, useState } from "react";
import { ResultCard } from "./ResultCard";
import { LoginForm } from "./LoginForm";
import type { ChatEntry } from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const TOKEN_STORAGE_KEY = "aiops_token";

const SAMPLE_QUESTIONS = [
  "How many critical vulnerabilities are currently open?",
  "Show employees earning more than 15 lakh with 5+ years experience",
  "Which team has the most open incidents?",
  "What is the procedure for a P1 incident?",
  "What are the SLA timelines for remediating vulnerabilities?",
];

export default function Home() {
  const [token, setToken] = useState<string | null>(null);
  const [tokenChecked, setTokenChecked] = useState(false);
  const [input, setInput] = useState("");
  const [entries, setEntries] = useState<ChatEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    // Token is sourced from localStorage after hydration.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setToken(localStorage.getItem(TOKEN_STORAGE_KEY));
    setTokenChecked(true);
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [entries, loading]);

  function handleLogin(newToken: string) {
    localStorage.setItem(TOKEN_STORAGE_KEY, newToken);
    setToken(newToken);
  }

  function handleLogout() {
    localStorage.removeItem(TOKEN_STORAGE_KEY);
    setToken(null);
    setEntries([]);
  }

  async function ask(question: string) {
    if (!question.trim() || loading || !token) return;
    setEntries((prev) => [...prev, { role: "user", text: question }]);
    setInput("");
    setLoading(true);

    try {
      const res = await fetch(`${API_URL}/api/agent`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ question }),
      });
      if (res.status === 401) {
        handleLogout();
        return;
      }
      const data = await res.json();
      if (!res.ok) {
        setEntries((prev) => [
          ...prev,
          { role: "error", text: data.detail ?? "Something went wrong." },
        ]);
      } else {
        setEntries((prev) => [...prev, { role: "assistant", result: data }]);
      }
    } catch {
      setEntries((prev) => [
        ...prev,
        { role: "error", text: "Could not reach the backend API." },
      ]);
    } finally {
      setLoading(false);
    }
  }

  if (!tokenChecked) return null;
  if (!token) return <LoginForm onLogin={handleLogin} />;

  return (
    <main className="h-screen flex flex-col items-center p-4 md:p-6 overflow-hidden">
      <div className="w-full max-w-4xl h-full flex flex-col gap-4 rounded-2xl border border-[var(--surface-border)] bg-[var(--surface)] backdrop-blur-sm p-4 md:p-5 shadow-[0_24px_80px_rgba(53,36,16,0.14)]">
        <div className="flex items-center justify-between gap-4">
          <div>
            <p className="text-xs tracking-[0.18em] uppercase text-[var(--muted)]">Agentic Ops Intelligence</p>
            <h1 className="text-2xl md:text-3xl font-semibold">AIOps Agent Assistant</h1>
          </div>
          <button
            onClick={handleLogout}
            className="text-xs border border-[var(--surface-border)] rounded-full px-3 py-1 text-[var(--muted)] hover:text-[var(--foreground)] hover:border-[var(--muted)] transition-colors"
          >
            Sign out
          </button>
        </div>
        <p className="text-sm text-[var(--muted)]">
          Ask questions about employees, servers, incidents, and vulnerabilities
          in plain English.
        </p>

        <div className="flex flex-wrap gap-2">
          {SAMPLE_QUESTIONS.map((q) => (
            <button
              key={q}
              onClick={() => ask(q)}
              className="text-xs border border-[var(--surface-border)] rounded-full px-3 py-1 text-[var(--muted)] hover:text-[var(--foreground)] hover:border-[var(--accent)] hover:bg-white/50 transition-colors"
            >
              {q}
            </button>
          ))}
        </div>

        <div className="flex-1 min-h-0 overflow-y-auto pr-1 rounded-xl border border-[var(--surface-border)] bg-white/45">
          <div className="flex flex-col gap-4 pb-2">
          {entries.map((entry, i) => {
            if (entry.role === "user") {
              return (
                <div key={i} className="self-end bg-[var(--accent)] text-white rounded-2xl px-4 py-2 max-w-[80%] mr-2 mt-2 shadow-sm">
                  {entry.text}
                </div>
              );
            }
            if (entry.role === "error") {
              return (
                <div key={i} className="border border-red-400 text-red-700 rounded-xl px-4 py-2 bg-red-50 mx-2 mt-2">
                  {entry.text}
                </div>
              );
            }
            return <ResultCard key={i} result={entry.result} />;
          })}
          {loading && (
            <div className="text-sm text-[var(--muted)] px-3 pb-2">Thinking...</div>
          )}
          <div ref={bottomRef} />
          </div>
        </div>

        <form
          onSubmit={(e) => {
            e.preventDefault();
            ask(input);
          }}
          className="flex gap-2"
        >
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask about employees, servers, incidents, vulnerabilities…"
            className="flex-1 border border-[var(--surface-border)] rounded-xl px-4 py-2 bg-white/60 focus:outline-none focus:ring-2 focus:ring-[var(--accent)]"
          />
          <button
            type="submit"
            disabled={loading}
            className="bg-[var(--accent)] hover:bg-[var(--accent-strong)] text-white rounded-xl px-5 py-2 disabled:opacity-50 transition-colors"
          >
            Ask
          </button>
        </form>
      </div>
    </main>
  );
}
