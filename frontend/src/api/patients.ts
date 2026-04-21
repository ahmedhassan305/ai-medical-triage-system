import { api } from "./client";
import type {
  ManagedPatientProfileCreateDto,
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

export async function findPatientByNationalId(
  nationalId: string,
): Promise<PatientProfileResponseDto> {
  const response = await api.get<PatientProfileResponseDto>(
    apiPaths.patients.byNationalId(nationalId),
  );
  return response.data;
}

export async function createManagedPatientProfile(
  payload: ManagedPatientProfileCreateDto,
): Promise<PatientProfileResponseDto> {
  const response = await api.post<PatientProfileResponseDto>(
    apiPaths.patients.create,
    payload,
  );
  return response.data;
}
