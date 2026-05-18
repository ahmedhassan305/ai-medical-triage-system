import { api } from "./client";
import type {
  LabPdfExtractionResponseDto,
  LabValueDto,
  TriageRequestDto,
  TriageResponseDto,
} from "./dto";
import { apiPaths } from "./paths";

export type { TriageLevel, TriageResponseDto as TriageResponse } from "./dto";

export async function triage(
  query: string,
  patientId?: number,
  labValues: LabValueDto[] = [],
): Promise<TriageResponseDto> {
  const payload: TriageRequestDto = {
    query,
    patient_id: patientId,
    lab_values: labValues,
  };
  const response = await api.post<TriageResponseDto>(apiPaths.triage, payload);
  return response.data;
}

export async function extractLabPdf(
  file: File,
  patientId?: number,
): Promise<LabPdfExtractionResponseDto> {
  const formData = new FormData();
  formData.append("file", file);
  if (patientId) {
    formData.append("patient_id", String(patientId));
  }
  const response = await api.post<LabPdfExtractionResponseDto>(
    apiPaths.labPdfExtract,
    formData,
    { headers: { "Content-Type": "multipart/form-data" } },
  );
  return response.data;
}
