import { api } from "./client";
import type {
  DoctorProfileResponseDto,
  DoctorProfileUpsertDto,
} from "./dto";
import { apiPaths } from "./paths";
import { AxiosError }   from "axios";
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
    const axiosError = error as AxiosError;
    // If user is not a doctor → backend returns 403 → ignore it
    if (axiosError?.response?.status === 403) {
      console.log("User is not a doctor, skipping doctor profile");
      return null;  
    }

    // Any other error → throw it (real problem)
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
