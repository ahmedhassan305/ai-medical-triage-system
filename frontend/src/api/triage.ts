import { api } from "./client";

export type TriageLevel = "low" | "medium" | "high";

export type TriageResponse = {
  triage_level: TriageLevel;
  summary: string;
  actions: string[];
  disclaimer: string;
};

export async function triage(query: string): Promise<TriageResponse> {
  const res = await api.post<TriageResponse>("/triage", { query });
  return res.data;
}
