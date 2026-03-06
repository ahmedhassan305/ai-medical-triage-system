import { useState } from "react";

import type { RoleType } from "../api/dto";
import SectionPanel from "./SectionPanel";

type AuthPanelProps = {
  loading: boolean;
  error: string | null;
  onLogin: (payload: { email: string; password: string }) => Promise<void>;
  onRegister: (payload: {
    email: string;
    password: string;
    role: RoleType;
  }) => Promise<void>;
};

export default function AuthPanel({
  loading,
  error,
  onLogin,
  onRegister,
}: AuthPanelProps) {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<RoleType>("patient");

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (mode === "login") {
      await onLogin({ email: email.trim(), password });
      return;
    }

    await onRegister({ email: email.trim(), password, role });
  }

  return (
    <div className="auth-shell">
      <div className="auth-shell__hero">
        <p className="hero__eyebrow">Clinical operations cockpit</p>
        <h1 className="hero__title">AI Medical Triage System</h1>
        <p className="hero__copy">
          Authenticate, manage patient and doctor profiles, run history-aware
          triage, coordinate appointments, and import records from one screen.
        </p>
        <div className="hero__stats">
          <div className="hero__stat">
            <span>FastAPI</span>
            <strong>CRM + triage API</strong>
          </div>
          <div className="hero__stat">
            <span>Reasoner</span>
            <strong>Ollama-backed summaries</strong>
          </div>
          <div className="hero__stat">
            <span>History-aware</span>
            <strong>Patient context in triage</strong>
          </div>
        </div>
      </div>

      <SectionPanel
        eyebrow="Access"
        title={mode === "login" ? "Sign in" : "Create account"}
        description="Use a patient, doctor, or admin account to unlock the relevant workspace."
      >
        <div className="segmented-control">
          <button
            type="button"
            className={mode === "login" ? "is-active" : ""}
            onClick={() => setMode("login")}
          >
            Login
          </button>
          <button
            type="button"
            className={mode === "register" ? "is-active" : ""}
            onClick={() => setMode("register")}
          >
            Register
          </button>
        </div>

        <form className="stack-lg" onSubmit={handleSubmit}>
          <div className="field">
            <label htmlFor="auth-email">Email</label>
            <input
              id="auth-email"
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              placeholder="doctor@clinic.local"
            />
          </div>

          <div className="field">
            <label htmlFor="auth-password">Password</label>
            <input
              id="auth-password"
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              placeholder="Minimum 8 characters"
            />
          </div>

          {mode === "register" ? (
            <div className="field">
              <label htmlFor="auth-role">Role</label>
              <select
                id="auth-role"
                value={role}
                onChange={(event) => setRole(event.target.value as RoleType)}
              >
                <option value="patient">Patient</option>
                <option value="doctor">Doctor</option>
                <option value="admin">Admin</option>
              </select>
            </div>
          ) : null}

          {error ? <div className="notice notice--error">{error}</div> : null}

          <button
            type="submit"
            className="button button--primary"
            disabled={loading || !email.trim() || password.length < 8}
          >
            {loading
              ? "Working..."
              : mode === "login"
                ? "Login"
                : "Create account"}
          </button>
        </form>
      </SectionPanel>
    </div>
  );
}
