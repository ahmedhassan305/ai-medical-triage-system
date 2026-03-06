import axios from "axios";

type ErrorPayload = {
  detail?: string;
  error?: {
    message?: string;
  };
};

export function getErrorMessage(error: unknown, fallback: string): string {
  if (!axios.isAxiosError(error)) {
    return fallback;
  }

  const payload = error.response?.data as ErrorPayload | undefined;
  if (typeof payload?.detail === "string" && payload.detail.trim()) {
    return payload.detail;
  }

  if (
    typeof payload?.error?.message === "string" &&
    payload.error.message.trim()
  ) {
    return payload.error.message;
  }

  if (typeof error.message === "string" && error.message.trim()) {
    return error.message;
  }

  return fallback;
}
