import { useState } from "react";

import type { RoleType } from "../api/dto";
import { useLanguage } from "../i18n/useLanguage";
import SectionPanel from "./SectionPanel";

type PatientSexOption = "" | "Male" | "Female";

type AuthPanelProps = {
  loading: boolean;
  error: string | null;
  onLogin: (payload: { email: string; password: string }) => Promise<void>;
  onRegister: (payload: {
    email: string;
    password: string;
    role: RoleType;
    full_name?: string;
    national_id?: string;
    sex?: Exclude<PatientSexOption, "">;
  }) => Promise<void>;
};

export default function AuthPanel({
  loading,
  error,
  onLogin,
  onRegister,
}: AuthPanelProps) {
  const { language, setLanguage, t } = useLanguage();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<RoleType>("patient");
  
  // Patient registration fields
  const [fullName, setFullName] = useState("");
  const [nationalId, setNationalId] = useState("");
  const [sex, setSex] = useState<PatientSexOption>("");

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (mode === "login") {
      await onLogin({ email: email.trim(), password });
      return;
    }

    const registerPayload: {
      email: string;
      password: string;
      role: RoleType;
      full_name?: string;
      national_id?: string;
      sex?: Exclude<PatientSexOption, "">;
    } = {
      email: email.trim(),
      password,
      role,
    };

    if (role === "patient") {
      registerPayload.full_name = fullName.trim();
      registerPayload.national_id = nationalId.trim();
      if (sex) {
        registerPayload.sex = sex;
      }
    }

    await onRegister(registerPayload);
  }

  const isPatientMode = mode === "register" && role === "patient";
  const canSubmit =
    mode === "login"
      ? !loading && !!email.trim() && password.length >= 8
      : !loading &&
        !!email.trim() &&
        password.length >= 8 &&
        (!isPatientMode ||
          (!!fullName.trim() && !!nationalId.trim() && !!sex));

  return (
    <div className="auth-shell">
      <div className="auth-shell__hero">
        <div className="language-toggle">
          <button
            type="button"
            className={language === "en" ? "is-active" : ""}
            onClick={() => setLanguage("en")}
          >
            {t("languageEnglish")}
          </button>
          <button
            type="button"
            className={language === "ar" ? "is-active" : ""}
            onClick={() => setLanguage("ar")}
          >
            {t("languageArabic")}
          </button>
        </div>
        <p className="hero__eyebrow">{t("operationsControlCenter")}</p>
        <h1 className="hero__title">AI Medical Triage System</h1>
        <p className="hero__copy">{t("profileAdminDescription")}</p>
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
        eyebrow={t("access")}
        title={mode === "login" ? t("signIn") : t("createAccount")}
        description={t("profileDescription")}
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
            <label htmlFor="auth-email">{t("email")}</label>
            <input
              id="auth-email"
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              placeholder="doctor@clinic.local"
            />
          </div>

          <div className="field">
            <label htmlFor="auth-password">{t("password")}</label>
            <input
              id="auth-password"
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              placeholder="Minimum 8 characters"
            />
          </div>

          {mode === "register" ? (
            <>
              <div className="field">
                <label htmlFor="auth-role">{t("accountType")}</label>
                <select
                  id="auth-role"
                  value={role}
                  onChange={(event) => {
                    setRole(event.target.value as RoleType);
                    // Clear patient fields when switching roles
                    if (event.target.value !== "patient") {
                      setFullName("");
                      setNationalId("");
                      setSex("");
                    }
                  }}
                >
                  <option value="patient">{t("patient")}</option>
                  <option value="doctor">{t("doctor")}</option>
                  <option value="admin">Admin</option>
                </select>
              </div>

              {isPatientMode ? (
                <>
                  <div className="field">
                    <label htmlFor="auth-full-name">{t("fullName")}</label>
                    <input
                      id="auth-full-name"
                      type="text"
                      value={fullName}
                      onChange={(event) => setFullName(event.target.value)}
                      placeholder="Your full name"
                      required
                    />
                  </div>

                  <div className="field">
                    <label htmlFor="auth-national-id">
                      Egyptian national ID
                    </label>
                    <input
                      id="auth-national-id"
                      type="text"
                      inputMode="numeric"
                      maxLength={14}
                      value={nationalId}
                      onChange={(event) => {
                        const cleaned = event.target.value
                          .replace(/\D/g, "")
                          .slice(0, 14);
                        setNationalId(cleaned);
                      }}
                      placeholder="14-digit الرقم القومي"
                      required
                    />
                    <small className="field__hint">
                      Used to derive date of birth and governorate information.
                    </small>
                  </div>

                  <div className="field">
                    <label htmlFor="auth-sex">{t("gender")}</label>
                    <select
                      id="auth-sex"
                      value={sex}
                      onChange={(event) =>
                        setSex(event.target.value as PatientSexOption)
                      }
                      required
                    >
                      <option value="">{t("selectGender")}</option>
                      <option value="Male">{t("male")}</option>
                      <option value="Female">{t("female")}</option>
                    </select>
                  </div>
                </>
              ) : null}
            </>
          ) : null}

          {error ? <div className="notice notice--error">{error}</div> : null}

          <button
            type="submit"
            className="button button--primary"
            disabled={!canSubmit}
          >
            {loading
              ? t("working")
              : mode === "login"
                ? t("login")
                : t("createAccount")}
          </button>
        </form>
      </SectionPanel>
    </div>
  );
}
