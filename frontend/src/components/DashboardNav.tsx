import type { RoleType, UserResponseDto } from "../api/dto";

export type DashboardTab =
  | "overview"
  | "profile"
  | "triage"
  | "appointments"
  | "visits"
  | "records";

type DashboardNavProps = {
  user: UserResponseDto;
  selectedTab: DashboardTab;
  onSelectTab: (tab: DashboardTab) => void;
  onLogout: () => void;
};

type NavItem = {
  id: DashboardTab;
  label: string;
  roles: RoleType[];
};

const NAV_ITEMS: NavItem[] = [
  { id: "overview", label: "Overview", roles: ["patient", "doctor", "admin"] },
  { id: "profile", label: "Profile", roles: ["patient", "doctor", "admin"] },
  { id: "triage", label: "Triage", roles: ["patient", "doctor", "admin"] },
  {
    id: "appointments",
    label: "Appointments",
    roles: ["patient", "doctor", "admin"],
  },
  { id: "visits", label: "Visits", roles: ["patient", "doctor", "admin"] },
  { id: "records", label: "Records", roles: ["doctor", "admin"] },
];

export default function DashboardNav({
  user,
  selectedTab,
  onSelectTab,
  onLogout,
}: DashboardNavProps) {
  const items = NAV_ITEMS.filter((item) => item.roles.includes(user.role));

  return (
    <aside className="dashboard-nav">
      <div className="dashboard-nav__brand">
        <p className="dashboard-nav__eyebrow">AI Medical Triage</p>
        <h1>Care workspace</h1>
        <p className="dashboard-nav__meta">
          {user.email}
          <span>{user.role.toUpperCase()}</span>
        </p>
      </div>

      <nav className="dashboard-nav__menu">
        {items.map((item) => (
          <button
            key={item.id}
            type="button"
            className={selectedTab === item.id ? "is-active" : ""}
            onClick={() => onSelectTab(item.id)}
          >
            {item.label}
          </button>
        ))}
      </nav>

      <button type="button" className="button button--ghost" onClick={onLogout}>
        Logout
      </button>
    </aside>
  );
}
