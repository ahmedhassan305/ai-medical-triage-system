import { api } from "./client";
import type {
  PatientProfileResponseDto,
  PatientProfileUpsertDto,
} from "./dto";
import { apiPaths } from "./paths";

export async function listPatients(): Promise<PatientProfileResponseDto[]> {
  const response = await api.get<PatientProfileResponseDto[]>(
    apiPaths.patients.list,
  );
  return response.data;
}

export async function fetchMyPatientProfile(): Promise<PatientProfileResponseDto> {
  const response = await api.get<PatientProfileResponseDto>(apiPaths.patients.me);
  return response.data;
}

export async function upsertMyPatientProfile(
  payload: PatientProfileUpsertDto,
): Promise<PatientProfileResponseDto> {
  const response = await api.post<PatientProfileResponseDto>(
    apiPaths.patients.me,
    payload,
  );
  return response.data;
}
