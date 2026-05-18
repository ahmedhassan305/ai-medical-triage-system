import { api } from "./client";
import type {
  DoctorProfileResponseDto,
  DoctorProfileUpsertDto,
  DoctorScheduleCreateDto,
  DoctorScheduleDto,
} from "./dto";
import { apiPaths } from "./paths";
import axios from "axios";

export async function listDoctors(): Promise<DoctorProfileResponseDto[]> {
  const response = await api.get<DoctorProfileResponseDto[]>(
    apiPaths.doctors.list,
  );
  return response.data;
}

// export async function fetchMyDoctorProfile(): Promise<DoctorProfileResponseDto> {
//   const response = await api.get<DoctorProfileResponseDto>(apiPaths.doctors.me);
//   return response.data;
// }
export async function fetchMyDoctorProfile(): Promise<DoctorProfileResponseDto | null> {
  try {
    const response = await api.get<DoctorProfileResponseDto>(apiPaths.doctors.me);
    return response.data;
  } catch (error: unknown) {
    if (axios.isAxiosError(error) && error.response?.status === 403) {
      return null;
    }

    throw error;
  }
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

export async function updateDoctorProfile(
  doctorId: number,
  payload: DoctorProfileUpsertDto,
): Promise<DoctorProfileResponseDto> {
  const response = await api.patch<DoctorProfileResponseDto>(
    apiPaths.doctors.byId(doctorId),
    payload,
  );
  return response.data;
}

export async function listDoctorSchedules(
  doctorId: number,
): Promise<DoctorScheduleDto[]> {
  const response = await api.get<DoctorScheduleDto[]>(
    apiPaths.doctors.schedules(doctorId),
  );
  return response.data;
}

export async function createDoctorSchedule(
  doctorId: number,
  payload: DoctorScheduleCreateDto,
): Promise<DoctorScheduleDto> {
  const response = await api.post<DoctorScheduleDto>(
    apiPaths.doctors.schedules(doctorId),
    payload,
  );
  return response.data;
}
