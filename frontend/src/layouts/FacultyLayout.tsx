import { Outlet, useLocation } from "react-router-dom";
import Sidebar from "../components/common/Sidebar";
import Topbar from "../components/common/Topbar";
import AccountMenu from "../components/common/AccountMenu";
import {useAuth} from "../context/AuthContext";

const facultyItems = [
  { label: "Dashboard", path: "/faculty" },
  { label: "My Preferences", path: "/faculty/preferences" },
  { label: "My Schedule", path: "/faculty/schedule" },
  { label: "Adjustment Requests", path: "/faculty/adjustments" },
  { label: "Profile", path: "/faculty/profile" },
];

export default function FacultyLayout() {
  const {user} = useAuth();
  const {pathname} = useLocation();
  const title = ({"/faculty": "Faculty Dashboard", "/faculty/preferences": "My Preferences", "/faculty/schedule": "My Schedule", "/faculty/adjustments": "Adjustment Requests", "/faculty/profile": "Faculty Profile"} as Record<string, string>)[pathname] ?? "Faculty Portal";
  return (
    <div className="dashboard-shell bg-slate-50">
      <a className="dashboard-skip-link" href="#dashboard-main">Skip to page content</a>
      <Sidebar
        title="CCS Faculty Scheduling"
        role="Faculty"
        items={facultyItems}
      />

      <div className="dashboard-content">
        <Topbar
          pageTitle={title}
          userName={user?.faculty?.display_code ?? user?.username}
          role="Faculty"
        />
        <AccountMenu />

        <main key={pathname} id="dashboard-main" tabIndex={-1} aria-label="Page content" className="dashboard-main p-4 sm:p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
