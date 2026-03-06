import type { TokenResponseDto } from "../api/dto";

const SESSION_STORAGE_KEY = "ai-medical-triage-session";

export function readSession(): TokenResponseDto | null {
  const rawValue = window.localStorage.getItem(SESSION_STORAGE_KEY);
  if (!rawValue) {
    return null;
  }

  try {
    return JSON.parse(rawValue) as TokenResponseDto;
  } catch {
    window.localStorage.removeItem(SESSION_STORAGE_KEY);
    return null;
  }
}

export function writeSession(session: TokenResponseDto): void {
  window.localStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(session));
}

export function clearSession(): void {
  window.localStorage.removeItem(SESSION_STORAGE_KEY);
}

export function getAccessToken(): string | null {
  return readSession()?.access_token ?? null;
}
