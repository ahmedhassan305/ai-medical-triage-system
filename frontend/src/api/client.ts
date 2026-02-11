import axios from "axios";

const baseURL = import.meta.env.VITE_API_BASE_URL;

if (!baseURL) {
  throw new Error("VITE_API_BASE_URL is required. Set it in frontend/.env");
}

export const api = axios.create({
  baseURL,
  headers: { "Content-Type": "application/json" },
});
