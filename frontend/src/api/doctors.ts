import { api } from "./client";
import type {
  DoctorProfileResponseDto,
  DoctorProfileUpsertDto,
} from "./dto";
import { apiPaths } from "./paths";

export async function listDoctors(): Promise<DoctorProfileResponseDto[]> {
  const response = await api.get<DoctorProfileResponseDto[]>(
    apiPaths.doctors.list,
  );
  return response.data;
}

export async function fetchMyDoctorProfile(): Promise<DoctorProfileResponseDto> {
  const response = await api.get<DoctorProfileResponseDto>(apiPaths.doctors.me);
  return response.data;
}

export async function upsertMyDoctorProfile(
  payload: DoctorProfileUpsertDto,
): Promise<DoctorProfileResponseDto> {
  const response = await api.post<DoctorProfileResponseDto>(
    apiPaths.doctors.me,
    payload,
  );
  return response.data;
}
