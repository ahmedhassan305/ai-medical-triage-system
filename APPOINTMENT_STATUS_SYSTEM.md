# Appointment Status System - Implementation Guide

## Overview

A production-ready appointment management system with robust status handling, color-coded badges, filtering, and grouping capabilities. No database schema modifications required.

## Architecture

### Core Files

#### 1. **Status Types & Enums** - [src/lib/appointmentStatus.ts](src/lib/appointmentStatus.ts)
Defines the appointment lifecycle and status mapping.

**Key Exports:**
- `AppointmentStatus` - Enum with states: PENDING, ACTIVE, UPCOMING, COMPLETED, REJECTED, CANCELLED
- `STATUS_DISPLAY_MAP` - Configuration for colors, icons, labels
- `normalizeBackendStatus()` - Converts backend statuses to normalized format
- Helper functions: `isActiveOrUpcoming()`, `isCompleted()`, `isRejectedOrCancelled()`

**Backend Status Mapping:**
```
requested      → PENDING
approved       → ACTIVE/UPCOMING
completed      → COMPLETED
rejected       → REJECTED
cancelled      → CANCELLED
```

**Color Scheme:**
- **Pending** (Blue) - ⏳ Awaiting approval
- **Active/Upcoming** (Green) - ✓ Confirmed appointments
- **Completed** (Gray) - ✔️ Past appointments
- **Rejected** (Red) - ✗ Doctor rejected
- **Cancelled** (Orange) - ⊘ User cancelled

#### 2. **Components** - [src/components/](src/components/)

##### **StatusBadge.tsx** - Status display components
Three reusable components:

```tsx
// Full badge with icon
<StatusBadge 
  status={AppointmentStatus.ACTIVE} 
  size="lg"
  showIcon
  showDescription
/>

// Minimal indicator
<StatusIndicator status={AppointmentStatus.PENDING} />

// Group header
<StatusGroupHeader 
  groupLabel="Active & Upcoming"
  count={5}
  isExpanded
  onToggle={() => {}}
/>
```

##### **AppointmentList.tsx** - Comprehensive list component
Features:
- Automatic grouping by status
- Full-text search (doctor, patient, specialty, reason)
- Status group filtering
- Expandable/collapsible sections
- Statistics dashboard
- Role-aware display (patient/doctor/admin)

```tsx
<AppointmentList
  appointments={data}
  doctors={doctors}
  patients={patients}
  currentRole="doctor"
  currentUserId={42}
/>
```

#### 3. **Filtering & Grouping** - [src/lib/appointmentFilters.ts](src/lib/appointmentFilters.ts)

Core utilities:
```tsx
// Normalize appointments
const normalized = normalizeAppointments(appointments);

// Group by status
const grouped = groupAppointmentsByStatus(normalized);
// → { active_upcoming, pending, completed, rejected_cancelled }

// Filter by group or status
const pending = filterAppointmentsByStatusGroup(normalized, 'pending');
const active = filterAppointmentsByStatus(normalized, AppointmentStatus.ACTIVE);

// Search
const results = searchAppointments(normalized, doctorMap, patientMap, query);

// Statistics
const stats = getAppointmentStats(normalized);
// → { total, activeUpcoming, pending, completed, rejectedCancelled }
```

#### 4. **Integration Helpers** - [src/lib/appointmentPanelIntegration.ts](src/lib/appointmentPanelIntegration.ts)

Helper functions for existing AppointmentsPanel integration:
```tsx
canApproveAppointment(apt)
canRejectAppointment(apt)
canCancelAppointment(apt)
canRescheduleAppointment(apt)
getAppointmentActionLabel(apt)
```

#### 5. **Demo Component** - [src/components/AppointmentStatusDemo.tsx](src/components/AppointmentStatusDemo.tsx)

Complete showcase with:
- 5 prototype doctors with diverse specialties
- 3 prototype patients with health profiles
- 8 prototype appointments covering all status states
- Role-based views (patient, doctor, admin)
- Interactive demonstration

## Usage Examples

### Basic Integration

```tsx
import { AppointmentList } from './components/AppointmentList';
import { normalizeAppointments } from './lib/appointmentFilters';

function MyComponent() {
  const [appointments, setAppointments] = useState([]);
  
  return (
    <AppointmentList
      appointments={appointments}
      doctors={doctors}
      patients={patients}
    />
  );
}
```

### Custom Status Display

```tsx
import { StatusBadge, StatusIndicator } from './components/StatusBadge';
import { normalizeBackendStatus } from './lib/appointmentStatus';

function AppointmentRow({ appointment }) {
  const status = normalizeBackendStatus(
    appointment.status,
    appointment.scheduled_for
  );
  
  return (
    <div>
      <StatusBadge status={status} size="md" showIcon />
    </div>
  );
}
```

### Filtering & Grouping

```tsx
import { 
  normalizeAppointments,
  groupAppointmentsByStatus,
  searchAppointments 
} from './lib/appointmentFilters';

const normalized = normalizeAppointments(appointments);
const grouped = groupAppointmentsByStatus(normalized);

// Get pending appointments
const pending = grouped.pending;

// Search specific appointments
const results = searchAppointments(
  normalized, 
  doctorMap, 
  patientMap,
  'cardiology'
);
```

### Status Checks

```tsx
import {
  AppointmentStatus,
  isActiveOrUpcoming,
  isCompleted,
  isPending
} from './lib/appointmentStatus';

const apt = {...};

if (isActiveOrUpcoming(apt.normalizedStatus)) {
  // Show cancel/reschedule options
}

if (isPending(apt.normalizedStatus)) {
  // Show approve/reject buttons (for doctor)
}
```

## Type Definitions

```typescript
// Core status type
type AppointmentStatus = 
  | "pending" 
  | "active" 
  | "upcoming" 
  | "completed" 
  | "rejected" 
  | "cancelled";

// Status groups
type AppointmentStatusGroup =
  | "active_upcoming"
  | "pending"
  | "completed"
  | "rejected_cancelled";

// Extended appointment with normalized status
type AppointmentWithStatus = AppointmentResponseDto & {
  normalizedStatus: AppointmentStatus;
};
```

## Data Flow

```
Backend API
  ↓
AppointmentResponseDto (status: string)
  ↓
normalizeBackendStatus() → AppointmentStatus enum
  ↓
AppointmentWithStatus (includes normalizedStatus)
  ↓
groupAppointmentsByStatus() → Organized by group
  ↓
AppointmentList (display with badges)
```

## Features

✅ **Status Normalization** - Converts backend strings to type-safe enums
✅ **Color-Coded Badges** - Semantic Tailwind colors with icons
✅ **Automatic Grouping** - Organize by status automatically
✅ **Full-Text Search** - Search across multiple fields
✅ **Role-Based Views** - Patient/Doctor/Admin filtering
✅ **Expandable Groups** - Collapse/expand status groups
✅ **Statistics** - Quick overview of appointment counts
✅ **Accessibility** - ARIA labels, keyboard navigation
✅ **Production-Ready** - TypeScript, modular, tested
✅ **No DB Changes** - Works with existing schema

## Testing the Demo

Run the demo component to see all features in action:

```tsx
import { AppointmentStatusDemo } from './components/AppointmentStatusDemo';

export function App() {
  return <AppointmentStatusDemo />;
}
```

The demo includes:
- 5 prototype Egyptian doctors with real specialties
- 3 prototype patients with health profiles
- 8 appointments covering all status states
- Interactive role switching (patient/doctor/admin)
- Status legend and info panels
- Live search and filtering

## Constraints Met

✅ **No Database Schema Changes** - Pure frontend implementation
✅ **Backend API Agnostic** - Works with any API returning status strings
✅ **Backward Compatible** - Existing AppointmentsPanel unmodified
✅ **Modular Design** - Use components independently
✅ **TypeScript Type-Safe** - Full type safety throughout
✅ **Production Quality** - Optimized, accessible, well-documented
✅ **No External Dependencies** - Uses React, TypeScript, Tailwind only

## Integration with Existing Code

### Option 1: Replace AppointmentsPanel
```tsx
// In App.tsx or parent component
import AppointmentList from './components/AppointmentList';

<AppointmentList
  appointments={appointments}
  doctors={doctors}
  patients={patients}
/>
```

### Option 2: Coexist with AppointmentsPanel
```tsx
// Both can display the same data
<AppointmentsPanel {...props} />
<AppointmentList {...props} />
```

### Option 3: Add to specific views
```tsx
// Add to patient dashboard
// Add to doctor appointment review
// Add to admin reporting
```

## Future Enhancements

- Export to CSV/PDF with status breakdown
- Calendar view integration
- Bulk status updates
- Appointment history/audit trail
- Email notifications on status changes
- Appointment reminders
- Rating/feedback after completion

## File Structure

```
frontend/src/
├── components/
│   ├── StatusBadge.tsx          # Status display components
│   ├── AppointmentList.tsx      # Main list component
│   └── AppointmentStatusDemo.tsx # Demo/test component
├── lib/
│   ├── appointmentStatus.ts      # Core types & enums
│   ├── appointmentFilters.ts     # Filtering & grouping
│   └── appointmentPanelIntegration.ts # Integration helpers
└── api/
    └── dto.ts                   # API types (existing)
```

## Notes

- **Backend Status Values**: Assumes backend returns "requested", "approved", "completed", or "rejected"
- **Date Calculation**: Uses `scheduled_for` and `requested_at` to determine if appointment is past/future
- **Role Detection**: Matches `user_id` on doctor/patient to current user for filtering
- **Search Performance**: O(n) complexity, suitable for <1000 appointments
- **Styling**: Tailwind CSS classes, customize colors in `STATUS_DISPLAY_MAP`

---

**Version**: 1.0.0
**Status**: Production Ready
**Last Updated**: April 2026
