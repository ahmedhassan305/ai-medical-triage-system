import { api } from "./client";
import type { TriageRequestDto, TriageResponseDto } from "./dto";
import { apiPaths } from "./paths";

export type { TriageLevel, TriageResponseDto as TriageResponse } from "./dto";

export async function triage(query: string): Promise<TriageResponseDto> {
  const payload: TriageRequestDto = { query };
  const res = await api.post<TriageResponseDto>(apiPaths.triage, payload);
  return res.data;
}
