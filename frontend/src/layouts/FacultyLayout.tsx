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
    <div className="flex min-h-screen flex-col bg-slate-50 md:flex-row">
      <Sidebar
        title="CCS Faculty Scheduling"
        role="Faculty"
        items={facultyItems}
      />

      <div className="flex min-w-0 flex-1 flex-col">
        <Topbar
          pageTitle={title}
          userName={user?.faculty?.display_code ?? user?.username}
          role="Faculty"
        />
        <AccountMenu />

        <main className="min-w-0 flex-1 p-4 sm:p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
