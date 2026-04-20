import { useMemo, useState } from "react";

import type {
  DoctorProfileResponseDto,
  DoctorProfileUpsertDto,
  PatientProfileResponseDto,
  PatientProfileUpsertDto,
  RoleType,
} from "../api/dto";
import { parseEgyptianNationalId } from "../lib/egyptianNationalId";
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
  national_id: "",
  current_governorate: "",
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
          national_id: patientProfile.national_id ?? "",
          current_governorate: patientProfile.current_governorate ?? "",
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

  const parsedNationalId = useMemo(
    () =>
      patientForm.national_id
        ? parseEgyptianNationalId(patientForm.national_id)
        : null,
    [patientForm.national_id],
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

  const dateOfBirth =
    parsedNationalId?.dateOfBirth ?? patientProfile?.date_of_birth ?? "Derived after validation";
  const inferredGovernorate =
    parsedNationalId?.governorate ?? patientProfile?.inferred_governorate ?? "Will be inferred from the national ID";
  const nationalIdHasValue = Boolean(patientForm.national_id?.trim());
  const nationalIdInvalid = nationalIdHasValue && !parsedNationalId;

  return (
    <div className="stack-lg">
      {role === "patient" || role === "admin" ? (
        <SectionPanel
          eyebrow="Patient profile"
          title="Demographics and identity"
          description="This profile powers patient-aware triage, appointments, and visit history. The national ID can derive date of birth and the governorate encoded inside the ID, while current residence stays editable."
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
              <label htmlFor="patient-sex">Gender</label>
              <select
                id="patient-sex"
                value={patientForm.sex}
                onChange={(event) =>
                  setPatientForm((current) => ({
                    ...current,
                    sex: event.target.value,
                  }))
                }
              >
                <option value="">Select gender</option>
                <option value="Male">Male</option>
                <option value="Female">Female</option>
              </select>
            </div>

            <div className="field">
              <label htmlFor="patient-national-id">Egyptian national ID</label>
              <input
                id="patient-national-id"
                inputMode="numeric"
                maxLength={14}
                value={patientForm.national_id ?? ""}
                onChange={(event) => {
                  const nextValue = event.target.value.replace(/\D/g, "").slice(0, 14);
                  const parsed = parseEgyptianNationalId(nextValue);
                  setPatientForm((current) => ({
                    ...current,
                    ...(() => {
                      const previousParsed = current.national_id
                        ? parseEgyptianNationalId(current.national_id)
                        : null;
                      const shouldPrefillGovernorate =
                        !current.current_governorate ||
                        current.current_governorate === previousParsed?.governorate;
                      return {
                        current_governorate:
                          parsed && shouldPrefillGovernorate
                            ? parsed.governorate
                            : current.current_governorate,
                      };
                    })(),
                    national_id: nextValue,
                    age: parsed?.age ?? current.age,
                  }));
                }}
                placeholder="14-digit الرقم القومي"
              />
              <small className="field__hint">
                Used to derive date of birth and the governorate encoded in the ID.
              </small>
              {nationalIdInvalid ? (
                <small className="field__error">
                  Enter a valid 14-digit Egyptian national ID to derive date of birth and governorate.
                </small>
              ) : null}
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
              <small className="field__hint">
                If the national ID is valid, age is updated automatically.
              </small>
            </div>

            <div className="field">
              <label htmlFor="patient-dob">Date of birth from national ID</label>
              <input id="patient-dob" value={dateOfBirth} readOnly />
            </div>

            <div className="field">
              <label htmlFor="patient-inferred-governorate">
                Governorate from national ID
              </label>
              <input
                id="patient-inferred-governorate"
                value={inferredGovernorate}
                readOnly
              />
            </div>

            <div className="field">
              <label htmlFor="patient-current-governorate">
                Current governorate / residence
              </label>
              <input
                id="patient-current-governorate"
                value={patientForm.current_governorate ?? ""}
                onChange={(event) =>
                  setPatientForm((current) => ({
                    ...current,
                    current_governorate: event.target.value,
                  }))
                }
                placeholder="Editable current residence"
              />
              <small className="field__hint">
                This may match the ID-based governorate, but it should reflect the patient’s current residence.
              </small>
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
                nationalIdInvalid ||
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
          description="This profile is used in visit creation, approvals, and doctor suggestions after triage."
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
