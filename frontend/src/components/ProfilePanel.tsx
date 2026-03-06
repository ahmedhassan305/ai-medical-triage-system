import { useState } from "react";

import type {
  DoctorProfileResponseDto,
  DoctorProfileUpsertDto,
  PatientProfileResponseDto,
  PatientProfileUpsertDto,
  RoleType,
} from "../api/dto";
import SectionPanel from "./SectionPanel";

type ProfilePanelProps = {
  role: RoleType;
  patientProfile: PatientProfileResponseDto | null;
  doctorProfile: DoctorProfileResponseDto | null;
  savingPatient: boolean;
  savingDoctor: boolean;
  onSavePatient: (payload: PatientProfileUpsertDto) => Promise<void>;
  onSaveDoctor: (payload: DoctorProfileUpsertDto) => Promise<void>;
};

const EMPTY_PATIENT_FORM: PatientProfileUpsertDto = {
  full_name: "",
  age: 0,
  sex: "",
  smoker: false,
  alcoholic: false,
  chronic_conditions: [],
};

const EMPTY_DOCTOR_FORM: DoctorProfileUpsertDto = {
  full_name: "",
  specialty: "",
  clinic: "",
};

export default function ProfilePanel({
  role,
  patientProfile,
  doctorProfile,
  savingPatient,
  savingDoctor,
  onSavePatient,
  onSaveDoctor,
}: ProfilePanelProps) {
  const [patientForm, setPatientForm] = useState<PatientProfileUpsertDto>(
    patientProfile
      ? {
          full_name: patientProfile.full_name,
          age: patientProfile.age,
          sex: patientProfile.sex,
          smoker: patientProfile.smoker,
          alcoholic: patientProfile.alcoholic,
          chronic_conditions: patientProfile.chronic_conditions,
        }
      : EMPTY_PATIENT_FORM,
  );
  const [doctorForm, setDoctorForm] = useState<DoctorProfileUpsertDto>(
    doctorProfile
      ? {
          full_name: doctorProfile.full_name,
          specialty: doctorProfile.specialty,
          clinic: doctorProfile.clinic,
        }
      : EMPTY_DOCTOR_FORM,
  );
  const [chronicConditionsInput, setChronicConditionsInput] = useState(
    patientProfile?.chronic_conditions.join(", ") ?? "",
  );

  async function submitPatientProfile(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await onSavePatient({
      ...patientForm,
      chronic_conditions: chronicConditionsInput
        .split(",")
        .map((item) => item.trim())
        .filter(Boolean),
    });
  }

  async function submitDoctorProfile(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await onSaveDoctor(doctorForm);
  }

  return (
    <div className="stack-lg">
      {role === "patient" || role === "admin" ? (
        <SectionPanel
          eyebrow="Patient profile"
          title="Demographics and risk factors"
          description="These fields drive history-aware triage and patient record workflows."
        >
          <form className="form-grid" onSubmit={submitPatientProfile}>
            <div className="field">
              <label htmlFor="patient-full-name">Full name</label>
              <input
                id="patient-full-name"
                value={patientForm.full_name}
                onChange={(event) =>
                  setPatientForm((current) => ({
                    ...current,
                    full_name: event.target.value,
                  }))
                }
              />
            </div>

            <div className="field">
              <label htmlFor="patient-age">Age</label>
              <input
                id="patient-age"
                type="number"
                min={0}
                max={130}
                value={patientForm.age}
                onChange={(event) =>
                  setPatientForm((current) => ({
                    ...current,
                    age: Number(event.target.value),
                  }))
                }
              />
            </div>

            <div className="field">
              <label htmlFor="patient-sex">Sex</label>
              <input
                id="patient-sex"
                value={patientForm.sex}
                onChange={(event) =>
                  setPatientForm((current) => ({
                    ...current,
                    sex: event.target.value,
                  }))
                }
              />
            </div>

            <div className="field field--full">
              <label htmlFor="patient-conditions">Chronic conditions</label>
              <input
                id="patient-conditions"
                value={chronicConditionsInput}
                onChange={(event) => setChronicConditionsInput(event.target.value)}
                placeholder="hypertension, asthma, diabetes"
              />
            </div>

            <label className="checkbox">
              <input
                type="checkbox"
                checked={patientForm.smoker}
                onChange={(event) =>
                  setPatientForm((current) => ({
                    ...current,
                    smoker: event.target.checked,
                  }))
                }
              />
              Smoker
            </label>

            <label className="checkbox">
              <input
                type="checkbox"
                checked={patientForm.alcoholic}
                onChange={(event) =>
                  setPatientForm((current) => ({
                    ...current,
                    alcoholic: event.target.checked,
                  }))
                }
              />
              Alcohol use
            </label>

            <button
              type="submit"
              className="button button--primary"
              disabled={
                savingPatient ||
                !patientForm.full_name.trim() ||
                !patientForm.sex.trim()
              }
            >
              {savingPatient ? "Saving..." : "Save patient profile"}
            </button>
          </form>
        </SectionPanel>
      ) : null}

      {role === "doctor" || role === "admin" ? (
        <SectionPanel
          eyebrow="Doctor profile"
          title="Clinical identity"
          description="This profile is used in visit creation, approvals, and doctor selection flows."
        >
          <form className="form-grid" onSubmit={submitDoctorProfile}>
            <div className="field">
              <label htmlFor="doctor-full-name">Full name</label>
              <input
                id="doctor-full-name"
                value={doctorForm.full_name}
                onChange={(event) =>
                  setDoctorForm((current) => ({
                    ...current,
                    full_name: event.target.value,
                  }))
                }
              />
            </div>

            <div className="field">
              <label htmlFor="doctor-specialty">Specialty</label>
              <input
                id="doctor-specialty"
                value={doctorForm.specialty}
                onChange={(event) =>
                  setDoctorForm((current) => ({
                    ...current,
                    specialty: event.target.value,
                  }))
                }
              />
            </div>

            <div className="field field--full">
              <label htmlFor="doctor-clinic">Clinic</label>
              <input
                id="doctor-clinic"
                value={doctorForm.clinic}
                onChange={(event) =>
                  setDoctorForm((current) => ({
                    ...current,
                    clinic: event.target.value,
                  }))
                }
              />
            </div>

            <button
              type="submit"
              className="button button--primary"
              disabled={
                savingDoctor ||
                !doctorForm.full_name.trim() ||
                !doctorForm.specialty.trim() ||
                !doctorForm.clinic.trim()
              }
            >
              {savingDoctor ? "Saving..." : "Save doctor profile"}
            </button>
          </form>
        </SectionPanel>
      ) : null}
    </div>
  );
}
