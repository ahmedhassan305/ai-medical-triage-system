import { useState } from "react";
import type { AppointmentResponseDto, DoctorProfileResponseDto, PatientProfileResponseDto } from "../api/dto";
import AppointmentList from "./AppointmentList";
import { AppointmentStatus } from "../lib/appointmentStatus";

/**
 * AppointmentStatusDemo - Test component showcasing appointment status system
 *
 * This component demonstrates:
 * - All appointment status states
 * - Color-coded badges
 * - Filtering and grouping functionality
 * - Role-based views (patient, doctor, admin)
 * - Prototype data with realistic doctors and appointments
 *
 * NOTE: For testing only. Uses mock data.
 */

// Prototype doctors with diverse specialties
const PROTOTYPE_DOCTORS: DoctorProfileResponseDto[] = [
  {
    id: 1,
    full_name: "Dr. Ahmed El-Sayed",
    specialty: "Cardiology",
    clinic: "Heart Care Center",
    area: "Downtown",
    city: "Cairo",
    user_id: 101,
    created_at: "2024-01-15T10:00:00Z",
    updated_at: "2024-01-15T10:00:00Z",
  },
  {
    id: 2,
    full_name: "Dr. Fatima Al-Zahra",
    specialty: "Pediatrics",
    clinic: "Children's Medical Institute",
    area: "Nasr City",
    city: "Cairo",
    user_id: 102,
    created_at: "2024-01-15T10:00:00Z",
    updated_at: "2024-01-15T10:00:00Z",
  },
  {
    id: 3,
    full_name: "Dr. Mohamed Hassan",
    specialty: "Orthopedic Surgery",
    clinic: "Bone & Joint Clinic",
    area: "6th of October",
    city: "Giza",
    user_id: 103,
    created_at: "2024-01-15T10:00:00Z",
    updated_at: "2024-01-15T10:00:00Z",
  },
  {
    id: 4,
    full_name: "Dr. Layla Morsi",
    specialty: "Neurology",
    clinic: "Brain & Spine Center",
    area: "Heliopolis",
    city: "Cairo",
    user_id: 104,
    created_at: "2024-01-15T10:00:00Z",
    updated_at: "2024-01-15T10:00:00Z",
  },
  {
    id: 5,
    full_name: "Dr. Karim Abdo",
    specialty: "Dermatology",
    clinic: "Skin & Beauty Clinic",
    area: "Maadi",
    city: "Cairo",
    user_id: 105,
    created_at: "2024-01-15T10:00:00Z",
    updated_at: "2024-01-15T10:00:00Z",
  },
];

// Prototype patients
const PROTOTYPE_PATIENTS: PatientProfileResponseDto[] = [
  {
    id: 1,
    full_name: "Amina Mohamed",
    age: 35,
    sex: "Female",
    user_id: 201,
    smoker: false,
    alcoholic: false,
    chronic_conditions: ["Hypertension"],
    created_at: "2024-01-20T10:00:00Z",
    updated_at: "2024-01-20T10:00:00Z",
  },
  {
    id: 2,
    full_name: "Hassan Omar",
    age: 42,
    sex: "Male",
    user_id: 202,
    smoker: true,
    alcoholic: false,
    chronic_conditions: ["Diabetes", "Hypertension"],
    created_at: "2024-01-20T10:00:00Z",
    updated_at: "2024-01-20T10:00:00Z",
  },
  {
    id: 3,
    full_name: "Sara Ahmed",
    age: 28,
    sex: "Female",
    user_id: 203,
    smoker: false,
    alcoholic: false,
    chronic_conditions: [],
    created_at: "2024-01-20T10:00:00Z",
    updated_at: "2024-01-20T10:00:00Z",
  },
];

// Prototype appointments demonstrating all status states
function createPrototypeAppointments(): AppointmentResponseDto[] {
  const today = new Date();
  const tomorrow = new Date(today.getTime() + 24 * 60 * 60 * 1000);
  const nextWeek = new Date(today.getTime() + 7 * 24 * 60 * 60 * 1000);
  const lastWeek = new Date(today.getTime() - 7 * 24 * 60 * 60 * 1000);
  const twoWeeksAgo = new Date(today.getTime() - 14 * 24 * 60 * 60 * 1000);

  return [
    // Active/Upcoming appointments
    {
      id: 1,
      patient_id: 1,
      doctor_id: 1,
      reason: "Heart checkup and ECG test",
      notes: "Patient has family history of heart disease",
      status: "approved",
      scheduled_for: tomorrow.toISOString(),
      requested_at: new Date(today.getTime() - 3 * 24 * 60 * 60 * 1000).toISOString(),
      clinic: {
        id: 1,
        name: "Heart Care Center",
        address: "123 Cardiac St, Cairo",
        area: "Downtown",
        city: "Cairo",
        is_active: true,
      },
    },
    {
      id: 2,
      patient_id: 2,
      doctor_id: 3,
      reason: "Knee pain evaluation",
      notes: "Right knee pain after sports injury",
      status: "approved",
      scheduled_for: nextWeek.toISOString(),
      requested_at: new Date(today.getTime() - 2 * 24 * 60 * 60 * 1000).toISOString(),
    },

    // Pending appointments
    {
      id: 3,
      patient_id: 3,
      doctor_id: 2,
      reason: "Vaccination follow-up",
      notes: "Child needs booster shots",
      status: "requested",
      scheduled_for: null,
      requested_at: today.toISOString(),
    },
    {
      id: 4,
      patient_id: 1,
      doctor_id: 4,
      reason: "Headache consultation",
      notes: "Chronic headaches affecting work",
      status: "requested",
      scheduled_for: null,
      requested_at: new Date(today.getTime() - 6 * 60 * 60 * 1000).toISOString(),
    },

    // Completed appointments
    {
      id: 5,
      patient_id: 2,
      doctor_id: 1,
      reason: "Regular heart examination",
      notes: "Routine annual checkup",
      status: "completed",
      scheduled_for: lastWeek.toISOString(),
      requested_at: new Date(lastWeek.getTime() - 10 * 24 * 60 * 60 * 1000).toISOString(),
    },
    {
      id: 6,
      patient_id: 3,
      doctor_id: 5,
      reason: "Acne treatment consultation",
      notes: "Discussing skincare options",
      status: "completed",
      scheduled_for: twoWeeksAgo.toISOString(),
      requested_at: new Date(twoWeeksAgo.getTime() - 14 * 24 * 60 * 60 * 1000).toISOString(),
    },

    // Rejected appointments
    {
      id: 7,
      patient_id: 1,
      doctor_id: 5,
      reason: "Cosmetic consultation",
      notes: "Looking into skin treatment options",
      status: "rejected",
      scheduled_for: null,
      requested_at: new Date(today.getTime() - 4 * 24 * 60 * 60 * 1000).toISOString(),
    },

    // Cancelled appointments
    {
      id: 8,
      patient_id: 2,
      doctor_id: 2,
      reason: "General pediatric checkup",
      notes: "Patient cancelled due to scheduling conflict",
      status: "cancelled",
      scheduled_for: nextWeek.toISOString(),
      requested_at: new Date(today.getTime() - 5 * 24 * 60 * 60 * 1000).toISOString(),
    },
  ];
}

type DemoViewType = "all" | "patient" | "doctor" | "admin";

export function AppointmentStatusDemo() {
  const [viewType, setViewType] = useState<DemoViewType>("admin");
  const [showDetails, setShowDetails] = useState(true);

  const appointments = createPrototypeAppointments();

  const getCurrentRoleProps = () => {
    switch (viewType) {
      case "patient":
        return {
          currentRole: "patient" as const,
          currentUserId: 201, // Amina's user_id
        };
      case "doctor":
        return {
          currentRole: "doctor" as const,
          currentUserId: 101, // Dr. Ahmed's user_id
        };
      case "admin":
      case "all":
      default:
        return {
          currentRole: "admin" as const,
          currentUserId: undefined,
        };
    }
  };

  const roleProps = getCurrentRoleProps();

  return (
    <div className="max-w-6xl mx-auto p-6 bg-gray-50 min-h-screen">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">
          Appointment Status System Demo
        </h1>
        <p className="text-gray-600">
          Comprehensive appointment management with status badges, filtering, and role-based views
        </p>
      </div>

      {/* Controls */}
      <div className="bg-white rounded-lg shadow-sm p-6 mb-8">
        <div className="space-y-4">
          <div>
            <h2 className="text-sm font-semibold text-gray-900 mb-3">
              View As:
            </h2>
            <div className="flex flex-wrap gap-2">
              {(["all", "patient", "doctor", "admin"] as DemoViewType[]).map(
                (view) => (
                  <button
                    key={view}
                    onClick={() => setViewType(view)}
                    className={`px-4 py-2 rounded-lg font-medium transition-colors text-sm ${
                      viewType === view
                        ? "bg-blue-600 text-white"
                        : "bg-gray-200 text-gray-700 hover:bg-gray-300"
                    }`}
                  >
                    {view.charAt(0).toUpperCase() + view.slice(1)}
                  </button>
                ),
              )}
            </div>
          </div>

          <div className="flex items-center gap-4 pt-2 border-t border-gray-200">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={showDetails}
                onChange={(e) => setShowDetails(e.target.checked)}
                className="rounded border-gray-300"
              />
              <span className="text-sm text-gray-700">Show Details</span>
            </label>
          </div>
        </div>
      </div>

      {/* Status Legend */}
      <div className="bg-white rounded-lg shadow-sm p-6 mb-8">
        <h2 className="text-sm font-semibold text-gray-900 mb-4">Status Legend:</h2>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-6">
          <StatusLegendItem status="pending" label="Pending" icon="⏳" color="blue" />
          <StatusLegendItem status="active" label="Active" icon="✓" color="green" />
          <StatusLegendItem
            status="upcoming"
            label="Upcoming"
            icon="📅"
            color="green"
          />
          <StatusLegendItem
            status="completed"
            label="Completed"
            icon="✔️"
            color="gray"
          />
          <StatusLegendItem
            status="rejected"
            label="Rejected"
            icon="✗"
            color="red"
          />
          <StatusLegendItem
            status="cancelled"
            label="Cancelled"
            icon="⊘"
            color="orange"
          />
        </div>
      </div>

      {/* Info Panel */}
      {showDetails && <InfoPanel viewType={viewType} />}

      {/* Main appointment list */}
      <div className="bg-white rounded-lg shadow-sm p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">
          Appointments {viewType !== "all" && `(${viewType})`}
        </h2>
        <AppointmentList
          appointments={appointments}
          doctors={PROTOTYPE_DOCTORS}
          patients={PROTOTYPE_PATIENTS}
          {...roleProps}
        />
      </div>

      {/* Footer */}
      <div className="mt-8 p-6 bg-blue-50 border border-blue-200 rounded-lg text-sm text-gray-700">
        <p className="font-semibold text-gray-900 mb-2">📌 Key Features:</p>
        <ul className="space-y-1 list-disc list-inside">
          <li>
            <strong>Status Normalization:</strong> Converts backend statuses to user-friendly format
          </li>
          <li>
            <strong>Color-Coded Badges:</strong> Visual status indicators with semantic colors
          </li>
          <li>
            <strong>Grouped Display:</strong> Appointments organized by status group
          </li>
          <li>
            <strong>Search & Filter:</strong> Find appointments by doctor, patient, or reason
          </li>
          <li>
            <strong>Role-Based Views:</strong> Shows relevant data based on user role
          </li>
          <li>
            <strong>Production-Ready:</strong> Modular, TypeScript, Tailwind CSS
          </li>
        </ul>
      </div>
    </div>
  );
}

type StatusLegendItemProps = {
  status: string;
  label: string;
  icon: string;
  color: string;
};

function StatusLegendItem({ status, label, icon, color }: StatusLegendItemProps) {
  const colorMap = {
    blue: "bg-blue-100 text-blue-900 border-blue-300",
    green: "bg-green-100 text-green-900 border-green-300",
    gray: "bg-gray-100 text-gray-700 border-gray-300",
    red: "bg-red-100 text-red-900 border-red-300",
    orange: "bg-orange-100 text-orange-900 border-orange-300",
  };

  return (
    <div className={`p-2 rounded border text-center ${colorMap[color as keyof typeof colorMap]}`}>
      <div className="text-lg mb-1">{icon}</div>
      <div className="text-xs font-medium">{label}</div>
    </div>
  );
}

type InfoPanelProps = {
  viewType: DemoViewType;
};

function InfoPanel({ viewType }: InfoPanelProps) {
  const infoMap: Record<DemoViewType, { title: string; content: string[] }> = {
    all: {
      title: "Admin View",
      content: [
        "See all appointments across the system",
        "No filtering by user association",
        "Full statistics across all appointments",
      ],
    },
    patient: {
      title: "Patient View (Amina Mohamed, ID: 201)",
      content: [
        "Shows only appointments created by or assigned to this patient",
        "Can see appointment status and doctor information",
        "Can request new appointments or follow up on pending ones",
      ],
    },
    doctor: {
      title: "Doctor View (Dr. Ahmed El-Sayed, ID: 101)",
      content: [
        "Shows appointments where this doctor is assigned",
        "Can review pending patient requests",
        "Can approve, reject, or complete appointments",
      ],
    },
  };

  const info = infoMap[viewType];

  return (
    <div className="bg-white rounded-lg shadow-sm p-6 mb-8 border-l-4 border-blue-500">
      <h2 className="text-base font-semibold text-gray-900 mb-2">{info.title}</h2>
      <ul className="space-y-1 text-sm text-gray-600 list-disc list-inside">
        {info.content.map((item, idx) => (
          <li key={idx}>{item}</li>
        ))}
      </ul>
    </div>
  );
}

export default AppointmentStatusDemo;
