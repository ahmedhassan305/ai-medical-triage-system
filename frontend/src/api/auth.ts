import { api } from "./client";
import type {
  LoginRequestDto,
  RegisterRequestDto,
  TokenResponseDto,
  UserResponseDto,
} from "./dto";
import { apiPaths } from "./paths";

export async function registerUser(
  payload: RegisterRequestDto,
): Promise<UserResponseDto> {
  const response = await api.post<UserResponseDto>(apiPaths.auth.register, payload);
  return response.data;
}

export async function loginUser(
  payload: LoginRequestDto,
): Promise<TokenResponseDto> {
  const response = await api.post<TokenResponseDto>(apiPaths.auth.login, payload);
  return response.data;
}

export async function fetchCurrentUser(): Promise<UserResponseDto> {
  const response = await api.get<UserResponseDto>(apiPaths.auth.me);
  return response.data;
}
