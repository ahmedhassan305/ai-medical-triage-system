import type { RoleType, UserResponseDto } from "../api/dto";
import { useLanguage } from "../i18n/useLanguage";

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
  label: Parameters<ReturnType<typeof useLanguage>["t"]>[0];
  roles: RoleType[];
};

const NAV_ITEMS: NavItem[] = [
  { id: "overview", label: "navOverview", roles: ["patient", "doctor", "admin"] },
  { id: "profile", label: "navProfile", roles: ["patient", "doctor", "admin"] },
  { id: "triage", label: "navTriage", roles: ["patient", "doctor", "admin"] },
  {
    id: "appointments",
    label: "navAppointments",
    roles: ["patient", "doctor", "admin"],
  },
  { id: "visits", label: "navVisits", roles: ["patient", "doctor", "admin"] },
  { id: "records", label: "navRecords", roles: ["doctor", "admin"] },
];

export default function DashboardNav({
  user,
  selectedTab,
  onSelectTab,
  onLogout,
}: DashboardNavProps) {
  const { language, setLanguage, t } = useLanguage();
  const items = NAV_ITEMS.filter((item) => item.roles.includes(user.role));
  const roleWorkspaceLabel =
    user.role === "admin"
      ? t("operationsControlCenter")
      : user.role === "doctor"
        ? t("clinicalWorkflowHub")
        : t("myCareWorkspace");
  const roleWorkspaceCopy =
    user.role === "admin"
      ? "Coverage, approvals, and system posture."
      : user.role === "doctor"
        ? "Appointments, visits, and record actions."
        : "Triage, booking, and follow-up in one place.";

  return (
    <aside className="dashboard-nav">
      <div className="dashboard-nav__brand">
        <p className="dashboard-nav__eyebrow">AI Medical Triage</p>
        <h1>{roleWorkspaceLabel}</h1>
        <p className="dashboard-nav__copy">{roleWorkspaceCopy}</p>
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
            {t(item.label)}
          </button>
        ))}
      </nav>

      <div className="language-toggle" aria-label="Language">
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

      <button type="button" className="button button--ghost" onClick={onLogout}>
        {t("logout")}
      </button>
    </aside>
  );
}
