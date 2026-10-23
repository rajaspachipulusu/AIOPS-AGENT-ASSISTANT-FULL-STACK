"use client";

import { useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export function LoginForm({ onLogin }: { onLogin: (token: string) => void }) {
  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_URL}/api/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      });
      const data = await res.json();
      if (!res.ok) {
        setError(data.detail ?? "Login failed");
        return;
      }
      onLogin(data.access_token);
    } catch {
      setError("Could not reach the backend API.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="min-h-screen flex items-center justify-center p-6">
      <form
        onSubmit={handleSubmit}
        className="w-full max-w-sm flex flex-col gap-4 border border-[var(--surface-border)] rounded-2xl p-6 bg-[var(--surface)] backdrop-blur-sm shadow-[0_20px_60px_rgba(53,36,16,0.14)]"
      >
        <div>
          <p className="text-xs tracking-[0.18em] uppercase text-[var(--muted)]">Agentic Ops Intelligence</p>
          <h1 className="text-xl font-semibold">AIOps Agent Assistant - Sign in</h1>
        </div>
        <input
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          placeholder="Username"
          className="border border-[var(--surface-border)] rounded-xl px-4 py-2 bg-white/60 focus:outline-none focus:ring-2 focus:ring-[var(--accent)]"
        />
        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="Password"
          className="border border-[var(--surface-border)] rounded-xl px-4 py-2 bg-white/60 focus:outline-none focus:ring-2 focus:ring-[var(--accent)]"
        />
        {error && <p className="text-sm text-red-700">{error}</p>}
        <button
          type="submit"
          disabled={loading}
          className="bg-[var(--accent)] hover:bg-[var(--accent-strong)] text-white rounded-xl px-4 py-2 disabled:opacity-50 transition-colors"
        >
          {loading ? "Signing in..." : "Sign in"}
        </button>
        <p className="text-xs text-[var(--muted)]">
          Demo credentials: admin / changeme123
        </p>
      </form>
    </main>
  );
}
