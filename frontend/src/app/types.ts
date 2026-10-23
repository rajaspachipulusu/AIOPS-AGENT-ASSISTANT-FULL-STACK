export type AgentResult = {
  tool_used: "query_database" | "search_documents";
  question: string;
  answer: string;
  sql?: string;
  rows?: Record<string, unknown>[];
  row_count?: number;
  sources?: { source: string; distance: number }[];
};

export type ChatEntry =
  | { role: "user"; text: string }
  | { role: "assistant"; result: AgentResult }
  | { role: "error"; text: string };
