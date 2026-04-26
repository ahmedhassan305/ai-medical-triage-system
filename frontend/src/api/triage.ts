import { api } from "./client";
import type {
  TriageDetailDto,
  TriageHistoryPageDto,
  TriageRequestDto,
  TriageResponseDto,
} from "./dto";
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

export async function fetchTriageHistory(
  limit = 10,
  offset = 0,
): Promise<TriageHistoryPageDto> {
  const response = await api.get<TriageHistoryPageDto>(apiPaths.triageHistory, {
    params: { limit, offset },
  });
  return response.data;
}

export async function fetchTriageDetail(triageId: number): Promise<TriageDetailDto> {
  const response = await api.get<TriageDetailDto>(apiPaths.triageDetail(triageId));
  return response.data;
}
