# Appointment Status System - Quick Reference

## 🚀 Quick Start

### Import Core Status Type
```tsx
import { AppointmentStatus, normalizeBackendStatus } from '../lib/appointmentStatus';
import { StatusBadge } from '../components/StatusBadge';
```

### Normalize and Display
```tsx
const status = normalizeBackendStatus(apt.status, apt.scheduled_for);
<StatusBadge status={status} />
```

### Use Complete List Component
```tsx
import AppointmentList from '../components/AppointmentList';

<AppointmentList
  appointments={appointments}
  doctors={doctors}
  patients={patients}
/>
```

---

## 📊 Status States

| State | Icon | Color | Meaning |
|-------|------|-------|---------|
| **PENDING** | ⏳ | Blue | Awaiting doctor approval |
| **ACTIVE** | ✓ | Green | Confirmed appointment |
| **UPCOMING** | 📅 | Green | Coming soon |
| **COMPLETED** | ✔️ | Gray | Finished |
| **REJECTED** | ✗ | Red | Doctor declined |
| **CANCELLED** | ⊘ | Orange | User cancelled |

---

## 🔄 Backend Mapping

```
Backend Status  →  Normalized Status
─────────────────────────────────────
"requested"     →  PENDING
"approved"      →  ACTIVE (if future) / COMPLETED (if past)
"completed"     →  COMPLETED
"rejected"      →  REJECTED
"cancelled"     →  CANCELLED
```

---

## 🎨 Components

### StatusBadge
```tsx
<StatusBadge 
  status={AppointmentStatus.PENDING}
  size="sm" | "md" | "lg"          // Default: "md"
  showIcon={true}                   // Default: true
  showDescription={false}           // Default: false
  className="custom-class"
/>
```

### StatusIndicator (minimal)
```tsx
<StatusIndicator 
  status={AppointmentStatus.ACTIVE}
  inline={true}                     // Default: true
/>
```

### StatusGroupHeader
```tsx
<StatusGroupHeader 
  groupLabel="Active & Upcoming"
  count={5}
  isExpanded={true}
  onToggle={() => console.log('toggled')}
/>
```

### AppointmentList (complete)
```tsx
<AppointmentList
  appointments={appointments}
  doctors={doctors}
  patients={patients}
  currentRole="doctor"              // Optional: "patient" | "doctor" | "admin"
  currentUserId={42}                // Optional: for role-based filtering
/>
```

---

## 🔍 Utilities

### Normalize Appointments
```tsx
import { normalizeAppointments } from '../lib/appointmentFilters';

const normalized = normalizeAppointments(appointments);
// Returns: AppointmentWithStatus[]
```

### Group by Status
```tsx
import { groupAppointmentsByStatus } from '../lib/appointmentFilters';

const grouped = groupAppointmentsByStatus(normalized);
// grouped.active_upcoming
// grouped.pending
// grouped.completed
// grouped.rejected_cancelled
```

### Filter by Group
```tsx
import { filterAppointmentsByStatusGroup } from '../lib/appointmentFilters';

const pending = filterAppointmentsByStatusGroup(normalized, 'pending');
```

### Filter by Status
```tsx
import { filterAppointmentsByStatus } from '../lib/appointmentFilters';

const upcoming = filterAppointmentsByStatus(normalized, AppointmentStatus.UPCOMING);
```

### Search Appointments
```tsx
import { searchAppointments } from '../lib/appointmentFilters';

const results = searchAppointments(
  normalized,
  doctorMap,
  patientMap,
  'cardiology'  // Searches: doctor name, specialty, patient name, reason
);
```

### Get Statistics
```tsx
import { getAppointmentStats } from '../lib/appointmentFilters';

const stats = getAppointmentStats(normalized);
// stats.total
// stats.activeUpcoming
// stats.pending
// stats.completed
// stats.rejectedCancelled
```

---

## ✅ Status Check Functions

```tsx
import {
  isActiveOrUpcoming,
  isCompleted,
  isRejectedOrCancelled,
  isPending
} from '../lib/appointmentStatus';

if (isActiveOrUpcoming(status)) { /* Show reschedule option */ }
if (isPending(status)) { /* Show approve/reject */ }
if (isCompleted(status)) { /* Show feedback form */ }
if (isRejectedOrCancelled(status)) { /* Show new request */ }
```

---

## 📋 Integration Helpers

```tsx
import {
  canApproveAppointment,
  canRejectAppointment,
  canCancelAppointment,
  canRescheduleAppointment,
  getAppointmentActionLabel
} from '../lib/appointmentPanelIntegration';

if (canApproveAppointment(apt)) { /* show button */ }
if (canCancelAppointment(apt)) { /* show button */ }

const label = getAppointmentActionLabel(apt); // "Review", "Manage", etc.
```

---

## 🎯 Common Patterns

### Display Appointment with Status
```tsx
function AppointmentCard({ appointment }) {
  const status = normalizeBackendStatus(
    appointment.status,
    appointment.scheduled_for
  );
  
  return (
    <div>
      <h3>{appointment.reason}</h3>
      <StatusBadge status={status} />
      <p>Scheduled: {appointment.scheduled_for}</p>
    </div>
  );
}
```

### Show Only Pending Appointments
```tsx
function PendingReview() {
  const normalized = normalizeAppointments(appointments);
  const pending = filterAppointmentsByStatusGroup(normalized, 'pending');
  
  return (
    <div>
      {pending.map(apt => (
        <AppointmentRow key={apt.id} appointment={apt} />
      ))}
    </div>
  );
}
```

### Role-Based Actions
```tsx
function AppointmentActions({ apt, role }) {
  return (
    <div>
      {role === 'doctor' && canApproveAppointment(apt) && (
        <button>Approve</button>
      )}
      {canCancelAppointment(apt) && (
        <button>Cancel</button>
      )}
    </div>
  );
}
```

### Create Status-Grouped List
```tsx
function AppointmentsByStatus() {
  const normalized = normalizeAppointments(appointments);
  const grouped = groupAppointmentsByStatus(normalized);
  
  return (
    <>
      <Section title="Upcoming" items={grouped.active_upcoming} />
      <Section title="Pending" items={grouped.pending} />
      <Section title="Completed" items={grouped.completed} />
      <Section title="Rejected" items={grouped.rejected_cancelled} />
    </>
  );
}
```

---

## 🎨 Customize Colors

In `appointmentStatus.ts`, modify `STATUS_DISPLAY_MAP`:

```tsx
[AppointmentStatus.PENDING]: {
  colors: {
    background: "bg-purple-100",  // Change to your color
    text: "text-purple-900",
    border: "border-purple-300",
    icon: "🔔",                   // Change icon
  },
  // ... rest of config
}
```

Tailwind colors available:
- Gray, Red, Orange, Yellow, Green, Blue, Indigo, Purple, Pink

---

## 📁 File Locations

```
✓ src/lib/appointmentStatus.ts           - Core types & enums
✓ src/lib/appointmentFilters.ts          - Filtering & grouping  
✓ src/lib/appointmentPanelIntegration.ts - Integration helpers
✓ src/components/StatusBadge.tsx         - Badge components
✓ src/components/AppointmentList.tsx     - Main list component
✓ src/components/AppointmentStatusDemo.tsx - Demo with test data
```

---

## 🧪 Testing with Demo

Import and use the demo component:

```tsx
import { AppointmentStatusDemo } from './components/AppointmentStatusDemo';

function App() {
  return <AppointmentStatusDemo />;
}
```

Features:
- 5 prototype Egyptian doctors
- 3 prototype patients
- 8 test appointments
- Role switcher
- Live search
- Status legend

---

## 🚫 Constraints Met

✅ No database schema changes
✅ Backend API agnostic (works with any status string)
✅ No external dependencies beyond React/TypeScript
✅ Fully type-safe
✅ Modular and reusable
✅ Production-ready code
✅ Accessible (ARIA labels, keyboard nav)

---

## 💡 Tips

- Use `normalizeAppointments()` once at the top level
- Memoize `doctorMap` and `patientMap` with `useMemo`
- Pass `currentRole` and `currentUserId` for automatic filtering
- Customize colors in `STATUS_DISPLAY_MAP`
- Component sizes: `sm` (compact), `md` (default), `lg` (prominent)
- Search works on: doctor name, specialty, patient name, reason

---

**Production Ready** | **Type-Safe** | **Zero Dependencies** | **Fully Documented**
