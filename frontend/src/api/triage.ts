import { api } from "./client";
import type { TriageRequestDto, TriageResponseDto } from "./dto";
import { apiPaths } from "./paths";

export type { TriageLevel, TriageResponseDto as TriageResponse } from "./dto";

export async function triage(
  query: string,
  patientId?: number,
): Promise<TriageResponseDto> {
  const payload: TriageRequestDto = {
    query,
    patient_id: patientId,
  };
  const response = await api.post<TriageResponseDto>(apiPaths.triage, payload);
  return response.data;
}
