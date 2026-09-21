import { Outlet } from "react-router-dom";
import Sidebar from "../components/common/Sidebar";
import Topbar from "../components/common/Topbar";

const facultyItems = [
  { label: "Dashboard", path: "/faculty" },
  { label: "My Preferences", path: "/faculty/preferences" },
  { label: "My Schedule", path: "/faculty/schedule" },
  { label: "Profile", path: "/faculty/profile" },
];

export default function FacultyLayout() {
  return (
    <div className="flex min-h-screen bg-slate-50">
      <Sidebar
        title="CCS Faculty Scheduling"
        role="Faculty"
        items={facultyItems}
      />

      <div className="flex min-w-0 flex-1 flex-col">
        <Topbar
          pageTitle="Faculty Dashboard"
          userName="Faculty User"
          role="Faculty"
        />

        <main className="flex-1 p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}