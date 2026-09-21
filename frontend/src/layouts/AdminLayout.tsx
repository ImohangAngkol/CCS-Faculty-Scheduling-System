import {
  Outlet,
  useLocation,
} from "react-router-dom";

import Sidebar from "../components/common/Sidebar";
import Topbar from "../components/common/Topbar";

import {
  useGA,
} from "../context/GAContext";


const adminItems = [
  {
    label: "Dashboard",
    path: "/admin",
  },
  {
    label: "Faculty",
    path: "/admin/faculty",
  },
  {
    label: "Subjects",
    path: "/admin/subjects",
  },
  {
    label: "Preferences",
    path: "/admin/preferences",
  },
  {
    label: "Generate Schedule",
    path: "/admin/generate",
  },
  {
    label: "Schedules",
    path: "/admin/schedules",
  },
  {
    label: "GA Analysis",
    path: "/admin/analysis",
  },
];


export default function AdminLayout() {

  const location =
    useLocation();


  const {
    loading,
    elapsedSeconds,
  } = useGA();


  // =====================================================
  // DYNAMIC PAGE TITLE
  // =====================================================

  function getPageTitle() {

    switch (location.pathname) {

      case "/admin":
        return "Admin Dashboard";

      case "/admin/faculty":
        return "Faculty Management";

      case "/admin/subjects":
        return "Subject Management";

      case "/admin/preferences":
        return "Faculty Preferences";

      case "/admin/generate":
        return "Generate Schedule";

      case "/admin/schedules":
        return "Generated Schedules";

      case "/admin/analysis":
        return "GA Analysis";

      default:
        return "Admin Portal";

    }

  }


  return (

    <div
      className="
        flex
        min-h-screen
        bg-slate-50
      "
    >

      {/* ================================================ */}
      {/* SIDEBAR */}
      {/* ================================================ */}

      <Sidebar
        title="CCS Faculty Scheduling"
        role="Admin"
        items={adminItems}
      />


      {/* ================================================ */}
      {/* MAIN AREA */}
      {/* ================================================ */}

      <div
        className="
          flex
          min-w-0
          flex-1
          flex-col
        "
      >

        {/* TOPBAR */}

        <Topbar
          pageTitle={getPageTitle()}
          userName="Administrator"
          role="Admin"
        />


        {/* ============================================ */}
        {/* GLOBAL GA RUNNING STATUS */}
        {/* ============================================ */}

        {loading && (

          <div
            className="
              flex
              items-center
              gap-3
              border-b
              border-[#0F766E]
              bg-[#0F766E]
              px-6
              py-3
              text-white
            "
          >

            <div
              className="
                h-4
                w-4
                animate-spin
                rounded-full
                border-2
                border-white
                border-t-transparent
              "
            />


            <span
              className="
                text-sm
                font-semibold
              "
            >
              Genetic Algorithm is running
            </span>


            <span
              className="
                text-sm
                text-teal-100
              "
            >
              {elapsedSeconds}s elapsed
            </span>

          </div>

        )}


        {/* ============================================ */}
        {/* CURRENT PAGE */}
        {/* ============================================ */}

        <main
          className="
            flex-1
            p-6
          "
        >

          <Outlet />

        </main>

      </div>

    </div>

  );
}