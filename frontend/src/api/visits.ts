import { api } from "./client";
import type { VisitCreateDto, VisitResponseDto } from "./dto";
import { apiPaths } from "./paths";

export async function createVisit(payload: VisitCreateDto): Promise<VisitResponseDto> {
  const response = await api.post<VisitResponseDto>(apiPaths.visits.create, payload);
  return response.data;
}

export async function listPatientVisits(
  patientId: number,
): Promise<VisitResponseDto[]> {
  const response = await api.get<VisitResponseDto[]>(
    apiPaths.visits.byPatient(patientId),
  );
  return response.data;
}

export async function listWorkspaceVisits(): Promise<VisitResponseDto[]> {
  const response = await api.get<VisitResponseDto[]>(apiPaths.visits.list);
  return response.data;
}
