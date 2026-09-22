import {
  BrowserRouter,
  Navigate,
  Route,
  Routes,
} from "react-router-dom";


import AdminLayout
  from "../layouts/AdminLayout";

import FacultyLayout
  from "../layouts/FacultyLayout";


import AdminDashboard
  from "../pages/admin/Dashboard";

import FacultyManagement
  from "../pages/admin/FacultyManagement";

import RoomAssignments
  from "../pages/admin/RoomAssignments";

import GenerateSchedule
  from "../pages/admin/GenerateSchedule";

import ChromosomeViewer
  from "../pages/admin/ChromosomeViewer";

import ScheduleView
  from "../pages/admin/ScheduleView";

import FitnessAnalysis
  from "../pages/admin/FitnessAnalysis";


function FacultyDashboard() {

  return (
    <div>
      Faculty Dashboard
    </div>
  );

}


function PlaceholderPage({
  title,
}: {
  title: string;
}) {

  return (

    <div
      className="
        rounded-xl
        border
        bg-white
        p-6
      "
    >

      <h1
        className="
          text-2xl
          font-bold
          text-slate-900
        "
      >
        {title}
      </h1>


      <p
        className="
          mt-2
          text-slate-500
        "
      >
        This page will be built next.
      </p>

    </div>

  );

}


export default function AppRoutes() {

  return (

    <BrowserRouter>

      <Routes>

        {/* ROOT */}

        <Route
          path="/"
          element={
            <Navigate
              to="/admin"
              replace
            />
          }
        />


        {/* ============================================= */}
        {/* ADMIN */}
        {/* ============================================= */}

        <Route
          path="/admin"
          element={
            <AdminLayout />
          }
        >

          <Route
            index
            element={
              <AdminDashboard />
            }
          />


          <Route
            path="faculty"
            element={
              <FacultyManagement />
            }
          />


          <Route
            path="subjects"
            element={
              <PlaceholderPage
                title="Subject Management"
              />
            }
          />


          <Route
            path="preferences"
            element={
              <PlaceholderPage
                title="Faculty Preferences"
              />
            }
          />


          <Route
            path="rooms"
            element={
              <RoomAssignments />
            }
          />


          <Route
            path="generate"
            element={
              <GenerateSchedule />
            }
          />


          {/* NEW */}

          <Route
            path="chromosomes"
            element={
              <ChromosomeViewer />
            }
          />


          <Route
            path="schedules"
            element={
              <ScheduleView />
            }
          />


          <Route
            path="analysis"
            element={
              <FitnessAnalysis />
            }
          />

        </Route>


        {/* ============================================= */}
        {/* FACULTY */}
        {/* ============================================= */}

        <Route
          path="/faculty"
          element={
            <FacultyLayout />
          }
        >

          <Route
            index
            element={
              <FacultyDashboard />
            }
          />


          <Route
            path="preferences"
            element={
              <PlaceholderPage
                title="My Preferences"
              />
            }
          />


          <Route
            path="schedule"
            element={
              <PlaceholderPage
                title="My Schedule"
              />
            }
          />


          <Route
            path="profile"
            element={
              <PlaceholderPage
                title="Profile"
              />
            }
          />

        </Route>


        {/* FALLBACK */}

        <Route
          path="*"
          element={
            <Navigate
              to="/admin"
              replace
            />
          }
        />

      </Routes>

    </BrowserRouter>

  );

}