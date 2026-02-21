export type TriageLevel = "low" | "medium" | "high";

export type TriageRequestDto = {
  query: string;
};

export type TriageResponseDto = {
  triage_level: TriageLevel;
  summary: string;
  actions: string[];
  disclaimer: string;
};
