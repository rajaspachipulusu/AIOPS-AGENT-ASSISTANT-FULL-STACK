"use client";

import type { AgentResult } from "./types";

export function ResultCard({ result }: { result: AgentResult }) {
  const columns =
    result.rows && result.rows.length > 0 ? Object.keys(result.rows[0]) : [];

  return (
    <div className="border border-[var(--surface-border)] rounded-xl p-4 flex flex-col gap-3 bg-white/70 mx-2">
      <span className="text-[10px] uppercase tracking-[0.12em] text-[var(--muted)]">
        {result.tool_used === "query_database"
          ? "Answered via database query"
          : "Answered via document search"}
      </span>

      <p className="text-sm whitespace-pre-wrap">{result.answer}</p>

      {result.sql && (
        <details className="text-xs">
          <summary className="cursor-pointer text-[var(--muted)]">
            Generated SQL
          </summary>
          <pre className="mt-2 p-2 bg-[#1f1b16] text-[#f5efe4] rounded overflow-x-auto">
            {result.sql}
          </pre>
        </details>
      )}

      {columns.length > 0 && (
        <div className="overflow-x-auto">
          <table className="w-full text-xs border-collapse">
            <thead>
              <tr>
                {columns.map((col) => (
                  <th
                    key={col}
                    className="text-left border-b border-[var(--surface-border)] px-2 py-1 font-semibold"
                  >
                    {col}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {result.rows!.map((row, i) => (
                <tr key={i} className="border-b border-[var(--surface-border)]">
                  {columns.map((col) => (
                    <td key={col} className="px-2 py-1">
                      {String(row[col])}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {result.row_count !== undefined && (
        <p className="text-xs text-[var(--muted)]">{result.row_count} row(s)</p>
      )}

      {result.sources && result.sources.length > 0 && (
        <details className="text-xs">
          <summary className="cursor-pointer text-[var(--muted)]">
            Sources ({result.sources.length})
          </summary>
          <ul className="mt-2 list-disc list-inside text-[var(--muted)]">
            {result.sources.map((s, i) => (
              <li key={i}>{s.source}</li>
            ))}
          </ul>
        </details>
      )}
    </div>
  );
}
