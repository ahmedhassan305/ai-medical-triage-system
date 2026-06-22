import { useMemo, useState } from "react";
import type { KeyboardEvent, PropsWithChildren } from "react";

import type { BodyDiagramTriageRequestDto, BodyRegionDto } from "../api/dto";
import {
  BODY_REGION_OPTIONS,
  COMMON_ASSOCIATED_SYMPTOMS,
} from "../lib/bodySymptomMap";
import CustomSelect from "./CustomSelect";

type BodySymptomSelectorProps = {
  loading: boolean;
  patientId?: number | null;
  language: "en" | "ar";
  onSubmit: (payload: BodyDiagramTriageRequestDto) => Promise<void>;
};

const SEVERITY_OPTIONS = [
  { value: "mild", label: "Mild" },
  { value: "moderate", label: "Moderate" },
  { value: "severe", label: "Severe" },
] as const;

const ONSET_OPTIONS = [
  { value: "sudden", label: "Sudden" },
  { value: "gradual", label: "Gradual" },
  { value: "after injury", label: "After injury" },
  { value: "unknown", label: "Unknown" },
] as const;

const DURATION_OPTIONS = [
  { value: "less than 1 hour", label: "Less than 1 hour" },
  { value: "today", label: "Today" },
  { value: "few days", label: "Few days" },
  { value: "more than a week", label: "More than a week" },
] as const;

function toggleValue(values: string[], value: string): string[] {
  return values.includes(value)
    ? values.filter((item) => item !== value)
    : [...values, value];
}

type BodyDiagramProps = {
  selectedRegion: BodyRegionDto;
  onSelect: (region: BodyRegionDto) => void;
};

const BODY_DIAGRAM_LABELS: Record<BodyRegionDto, string> = {
  head: "Head",
  face: "Face",
  neck: "Neck",
  chest: "Chest",
  abdomen: "Abdomen",
  pelvis_urinary: "Pelvis/Urinary",
  back: "Back",
  shoulder: "Shoulder",
  arm: "Arm",
  hand_wrist: "Hand/Wrist",
  hip: "Hip",
  leg: "Leg",
  knee: "Knee",
  foot_ankle: "Foot/Ankle",
  skin: "Skin",
};

function BodyRegionShape({
  region,
  selectedRegion,
  onSelect,
  children,
}: PropsWithChildren<BodyDiagramProps & { region: BodyRegionDto }>) {
  const isActive = selectedRegion === region;

  function handleKeyDown(event: KeyboardEvent<SVGGElement>) {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      onSelect(region);
    }
  }

  return (
    <g
      role="button"
      tabIndex={0}
      className={`body-diagram__region ${isActive ? "is-active" : ""}`}
      aria-label={BODY_DIAGRAM_LABELS[region]}
      aria-pressed={isActive}
      onClick={() => onSelect(region)}
      onKeyDown={handleKeyDown}
    >
      <title>{BODY_DIAGRAM_LABELS[region]}</title>
      {children}
    </g>
  );
}

function HumanBodyDiagram({ selectedRegion, onSelect }: BodyDiagramProps) {
  return (
    <div className="body-diagram-shell" aria-label="Human body diagram selector">
      <svg
        className="body-diagram"
        viewBox="0 0 420 520"
        role="img"
        aria-labelledby="body-diagram-title body-diagram-desc"
      >
        <title id="body-diagram-title">Clickable human body diagram</title>
        <desc id="body-diagram-desc">
          Select a body region to choose symptoms for medical triage.
        </desc>
        <defs>
          <linearGradient id="bodyFigureFill" x1="0" x2="1" y1="0" y2="1">
            <stop offset="0%" stopColor="#ffffff" stopOpacity="0.96" />
            <stop offset="100%" stopColor="#e7f3f0" stopOpacity="0.9" />
          </linearGradient>
          <radialGradient id="bodyFigureGlow" cx="50%" cy="34%" r="64%">
            <stop offset="0%" stopColor="#0f766e" stopOpacity="0.14" />
            <stop offset="100%" stopColor="#0f766e" stopOpacity="0" />
          </radialGradient>
        </defs>

        <path
          className="body-diagram__halo"
          d="M118 38 C156 40 184 68 187 112 C200 128 210 156 212 198 L219 330 C221 372 190 406 160 392 L162 494 H78 L80 392 C50 406 19 372 21 330 L28 198 C30 156 40 128 53 112 C56 68 80 40 118 38 Z"
        />
        <path
          className="body-diagram__halo"
          d="M302 38 C340 40 364 68 367 112 C380 128 390 156 392 198 L399 330 C401 372 370 406 340 392 L342 494 H258 L260 392 C230 406 199 372 201 330 L208 198 C210 156 220 128 233 112 C236 68 264 40 302 38 Z"
        />

        <text x="120" y="28" className="body-diagram__label">
          Front
        </text>
        <text x="300" y="28" className="body-diagram__label">
          Back
        </text>

        <BodyRegionShape
          region="skin"
          selectedRegion={selectedRegion}
          onSelect={onSelect}
        >
          <path d="M120 42 C151 42 170 64 166 96 C165 107 161 115 154 122 C184 130 200 154 202 190 L209 306 C212 330 197 348 177 343 L160 257 L153 352 L166 488 H132 L122 366 H118 L108 488 H74 L87 352 L80 257 L63 343 C43 348 28 330 31 306 L38 190 C40 154 56 130 86 122 C79 115 75 107 74 96 C70 64 89 42 120 42 Z" />
          <path d="M300 42 C331 42 350 64 346 96 C345 107 341 115 334 122 C364 130 380 154 382 190 L389 306 C392 330 377 348 357 343 L340 257 L333 352 L346 488 H312 L302 366 H298 L288 488 H254 L267 352 L260 257 L243 343 C223 348 208 330 211 306 L218 190 C220 154 236 130 266 122 C259 115 255 107 254 96 C250 64 269 42 300 42 Z" />
        </BodyRegionShape>

        <BodyRegionShape
          region="head"
          selectedRegion={selectedRegion}
          onSelect={onSelect}
        >
          <path d="M120 44 C139 44 153 59 153 78 C153 98 139 112 120 112 C101 112 87 98 87 78 C87 59 101 44 120 44 Z" />
          <path d="M300 44 C319 44 333 59 333 78 C333 98 319 112 300 112 C281 112 267 98 267 78 C267 59 281 44 300 44 Z" />
        </BodyRegionShape>

        <BodyRegionShape
          region="face"
          selectedRegion={selectedRegion}
          onSelect={onSelect}
        >
          <path d="M120 60 C134 60 144 70 144 83 C144 98 134 108 120 108 C106 108 96 98 96 83 C96 70 106 60 120 60 Z" />
        </BodyRegionShape>

        <BodyRegionShape
          region="neck"
          selectedRegion={selectedRegion}
          onSelect={onSelect}
        >
          <path d="M104 100 H136 Q142 100 142 108 V120 Q142 128 134 130 H106 Q98 128 98 120 V108 Q98 100 104 100 Z" />
          <path d="M284 100 H316 Q322 100 322 108 V120 Q322 128 314 130 H286 Q278 128 278 120 V108 Q278 100 284 100 Z" />
        </BodyRegionShape>

        <BodyRegionShape
          region="shoulder"
          selectedRegion={selectedRegion}
          onSelect={onSelect}
        >
          <path d="M62 138 C78 124 96 121 112 128 L110 160 L60 169 Z" />
          <path d="M128 128 C144 121 162 124 178 138 L180 169 L130 160 Z" />
          <path d="M242 138 C258 124 276 121 292 128 L290 160 L240 169 Z" />
          <path d="M308 128 C324 121 342 124 358 138 L360 169 L310 160 Z" />
        </BodyRegionShape>

        <BodyRegionShape
          region="chest"
          selectedRegion={selectedRegion}
          onSelect={onSelect}
        >
          <path d="M80 132 C94 126 146 126 160 132 L153 224 H87 Z" />
        </BodyRegionShape>

        <BodyRegionShape
          region="back"
          selectedRegion={selectedRegion}
          onSelect={onSelect}
        >
          <path d="M260 132 C274 126 326 126 340 132 L333 250 H267 Z" />
        </BodyRegionShape>

        <BodyRegionShape
          region="abdomen"
          selectedRegion={selectedRegion}
          onSelect={onSelect}
        >
          <path d="M87 224 H153 L147 304 H93 Z" />
        </BodyRegionShape>

        <BodyRegionShape
          region="pelvis_urinary"
          selectedRegion={selectedRegion}
          onSelect={onSelect}
        >
          <path d="M94 304 H146 C154 318 158 336 160 356 H80 C82 336 86 318 94 304 Z" />
        </BodyRegionShape>

        <BodyRegionShape
          region="hip"
          selectedRegion={selectedRegion}
          onSelect={onSelect}
        >
          <path d="M262 250 H338 C346 268 350 292 352 318 H248 C250 292 254 268 262 250 Z" />
        </BodyRegionShape>

        <BodyRegionShape
          region="arm"
          selectedRegion={selectedRegion}
          onSelect={onSelect}
        >
          <path d="M60 164 L84 170 L69 310 C62 314 49 312 42 306 Z" />
          <path d="M156 170 L180 164 L198 306 C191 312 178 314 171 310 Z" />
          <path d="M240 164 L264 170 L249 310 C242 314 229 312 222 306 Z" />
          <path d="M336 170 L360 164 L378 306 C371 312 358 314 351 310 Z" />
        </BodyRegionShape>

        <BodyRegionShape
          region="hand_wrist"
          selectedRegion={selectedRegion}
          onSelect={onSelect}
        >
          <path d="M52 310 C64 310 73 319 73 331 C73 343 64 352 52 352 C40 352 31 343 31 331 C31 319 40 310 52 310 Z" />
          <path d="M188 310 C200 310 209 319 209 331 C209 343 200 352 188 352 C176 352 167 343 167 331 C167 319 176 310 188 310 Z" />
          <path d="M232 310 C244 310 253 319 253 331 C253 343 244 352 232 352 C220 352 211 343 211 331 C211 319 220 310 232 310 Z" />
          <path d="M368 310 C380 310 389 319 389 331 C389 343 380 352 368 352 C356 352 347 343 347 331 C347 319 356 310 368 310 Z" />
        </BodyRegionShape>

        <BodyRegionShape
          region="leg"
          selectedRegion={selectedRegion}
          onSelect={onSelect}
        >
          <path d="M87 354 H116 L108 456 H76 Z" />
          <path d="M124 354 H153 L164 456 H132 Z" />
          <path d="M267 318 H296 L288 456 H256 Z" />
          <path d="M304 318 H333 L344 456 H312 Z" />
        </BodyRegionShape>

        <BodyRegionShape
          region="knee"
          selectedRegion={selectedRegion}
          onSelect={onSelect}
        >
          <path d="M94 396 C107 396 117 406 117 419 C117 432 107 442 94 442 C81 442 71 432 71 419 C71 406 81 396 94 396 Z" />
          <path d="M146 396 C159 396 169 406 169 419 C169 432 159 442 146 442 C133 442 123 432 123 419 C123 406 133 396 146 396 Z" />
          <path d="M274 396 C287 396 297 406 297 419 C297 432 287 442 274 442 C261 442 251 432 251 419 C251 406 261 396 274 396 Z" />
          <path d="M326 396 C339 396 349 406 349 419 C349 432 339 442 326 442 C313 442 303 432 303 419 C303 406 313 396 326 396 Z" />
        </BodyRegionShape>

        <BodyRegionShape
          region="foot_ankle"
          selectedRegion={selectedRegion}
          onSelect={onSelect}
        >
          <path d="M74 456 H110 L108 488 H62 Q60 472 74 456 Z" />
          <path d="M132 456 H166 Q180 472 178 488 H132 Z" />
          <path d="M254 456 H290 L288 488 H242 Q240 472 254 456 Z" />
          <path d="M312 456 H346 Q360 472 358 488 H312 Z" />
        </BodyRegionShape>
      </svg>

      <div className="body-diagram-selection">
        <span className="micro-label">Selected region</span>
        <strong>{BODY_DIAGRAM_LABELS[selectedRegion]}</strong>
      </div>
    </div>
  );
}

export default function BodySymptomSelector({
  loading,
  patientId,
  language,
  onSubmit,
}: BodySymptomSelectorProps) {
  const [selectedRegion, setSelectedRegion] = useState<BodyRegionDto>("chest");
  const [mainSymptoms, setMainSymptoms] = useState<string[]>([]);
  const [severity, setSeverity] =
    useState<BodyDiagramTriageRequestDto["severity"]>("moderate");
  const [onset, setOnset] =
    useState<BodyDiagramTriageRequestDto["onset"]>("unknown");
  const [duration, setDuration] =
    useState<BodyDiagramTriageRequestDto["duration"]>("today");
  const [associatedSymptoms, setAssociatedSymptoms] = useState<string[]>([]);
  const [freeText, setFreeText] = useState("");
  const [localError, setLocalError] = useState<string | null>(null);

  const selectedRegionOption = useMemo(
    () =>
      BODY_REGION_OPTIONS.find((option) => option.id === selectedRegion) ??
      BODY_REGION_OPTIONS[0],
    [selectedRegion],
  );

  function handleRegionSelect(region: BodyRegionDto) {
    setSelectedRegion(region);
    setMainSymptoms([]);
    setLocalError(null);
  }

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (mainSymptoms.length === 0) {
      setLocalError("Select at least one symptom for the chosen body part.");
      return;
    }
    setLocalError(null);
    await onSubmit({
      input_method: "body_diagram",
      selected_body_region: selectedRegion,
      main_symptoms: mainSymptoms,
      severity,
      onset,
      duration,
      associated_symptoms: associatedSymptoms,
      patient_free_text: freeText.trim(),
      patient_id: patientId ?? undefined,
      language,
    });
  }

  return (
    <div className="body-symptom-selector">
      <div className="result-card__meta">
        <div>
          <p className="micro-label">Body symptom selector</p>
          <h3>Choose where symptoms are strongest</h3>
        </div>
        <span className="badge badge--neutral">MVP</span>
      </div>

      <form className="stack-md" onSubmit={handleSubmit}>
        <HumanBodyDiagram
          selectedRegion={selectedRegion}
          onSelect={handleRegionSelect}
        />

        <div className="body-region-grid">
          {BODY_REGION_OPTIONS.map((region) => (
            <button
              key={region.id}
              type="button"
              className={`body-region-button ${
                selectedRegion === region.id ? "is-active" : ""
              }`}
              onClick={() => handleRegionSelect(region.id)}
            >
              {region.label}
            </button>
          ))}
        </div>

        <div className="body-symptom-step">
          <p className="micro-label">
            Symptoms for {selectedRegionOption.label}
          </p>
          <div className="symptom-chip-grid">
            {selectedRegionOption.symptoms.map((symptom) => (
              <button
                key={symptom}
                type="button"
                className={`symptom-chip ${
                  mainSymptoms.includes(symptom) ? "is-active" : ""
                }`}
                onClick={() => setMainSymptoms((current) => toggleValue(current, symptom))}
              >
                {symptom}
              </button>
            ))}
          </div>
        </div>

        <div className="form-grid">
          <div className="field">
            <label htmlFor="body-severity">Severity</label>
            <CustomSelect
              id="body-severity"
              value={severity}
              onChange={(value) =>
                setSeverity(value as BodyDiagramTriageRequestDto["severity"])
              }
              options={[...SEVERITY_OPTIONS]}
            />
          </div>

          <div className="field">
            <label htmlFor="body-onset">Onset</label>
            <CustomSelect
              id="body-onset"
              value={onset}
              onChange={(value) =>
                setOnset(value as BodyDiagramTriageRequestDto["onset"])
              }
              options={[...ONSET_OPTIONS]}
            />
          </div>

          <div className="field">
            <label htmlFor="body-duration">Duration</label>
            <CustomSelect
              id="body-duration"
              value={duration}
              onChange={(value) =>
                setDuration(value as BodyDiagramTriageRequestDto["duration"])
              }
              options={[...DURATION_OPTIONS]}
            />
          </div>
        </div>

        <div className="body-symptom-step">
          <p className="micro-label">Associated symptoms</p>
          <div className="symptom-chip-grid">
            {COMMON_ASSOCIATED_SYMPTOMS.map((symptom) => (
              <button
                key={symptom}
                type="button"
                className={`symptom-chip symptom-chip--secondary ${
                  associatedSymptoms.includes(symptom) ? "is-active" : ""
                }`}
                onClick={() =>
                  setAssociatedSymptoms((current) => toggleValue(current, symptom))
                }
              >
                {symptom}
              </button>
            ))}
          </div>
        </div>

        <div className="field">
          <label htmlFor="body-free-text">Optional extra details</label>
          <textarea
            id="body-free-text"
            rows={3}
            value={freeText}
            onChange={(event) => setFreeText(event.target.value)}
            placeholder="Add anything important, such as trigger, spread, or what makes it better/worse."
          />
        </div>

        {localError ? (
          <div className="notice notice--error" role="alert">
            {localError}
          </div>
        ) : null}

        <button
          type="submit"
          className="button button--primary"
          disabled={loading || mainSymptoms.length === 0}
        >
          {loading ? "Checking symptoms..." : "Get body-based assessment"}
        </button>
      </form>
    </div>
  );
}
