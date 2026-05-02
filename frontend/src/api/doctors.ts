import { api } from "./client";
import type {
  DoctorProfileResponseDto,
  DoctorProfileUpsertDto,
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
