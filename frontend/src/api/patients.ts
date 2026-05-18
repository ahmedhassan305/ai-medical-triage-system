import { api } from "./client";
import type {
  ManagedPatientProfileCreateDto,
  PatientMedicalHistoryEntryCreateDto,
  PatientMedicalHistoryEntryResponseDto,
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

export async function listPatientMedicalHistory(
  patientId: number,
): Promise<PatientMedicalHistoryEntryResponseDto[]> {
  const response = await api.get<PatientMedicalHistoryEntryResponseDto[]>(
    apiPaths.patients.medicalHistory(patientId),
  );
  return response.data;
}

export async function createPatientMedicalHistoryEntry(
  patientId: number,
  payload: PatientMedicalHistoryEntryCreateDto,
): Promise<PatientMedicalHistoryEntryResponseDto> {
  const response = await api.post<PatientMedicalHistoryEntryResponseDto>(
    apiPaths.patients.medicalHistory(patientId),
    payload,
  );
  return response.data;
}
