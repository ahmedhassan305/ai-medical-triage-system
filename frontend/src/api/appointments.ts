import { api } from "./client";
import type {
  AppointmentCreateDto,
  AppointmentResponseDto,
  AppointmentStatusUpdateDto,
} from "./dto";
import { apiPaths } from "./paths";

export async function listAppointments(): Promise<AppointmentResponseDto[]> {
  const response = await api.get<AppointmentResponseDto[]>(
    apiPaths.appointments.list,
  );
  return response.data;
}

export async function createAppointment(
  payload: AppointmentCreateDto,
): Promise<AppointmentResponseDto> {
  const response = await api.post<AppointmentResponseDto>(
    apiPaths.appointments.create,
    payload,
  );
  return response.data;
}

export async function updateAppointmentStatus(
  appointmentId: number,
  payload: AppointmentStatusUpdateDto,
): Promise<AppointmentResponseDto> {
  const response = await api.patch<AppointmentResponseDto>(
    apiPaths.appointments.status(appointmentId),
    payload,
  );
  return response.data;
}
