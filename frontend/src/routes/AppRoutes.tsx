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

import GenerateSchedule
  from "../pages/admin/GenerateSchedule";

import ScheduleView
  from "../pages/admin/ScheduleView";

import FitnessAnalysis
  from "../pages/admin/FitnessAnalysis";

import RoomAssignments
  from "../pages/admin/RoomAssignments";


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

        {/* ========================================= */}
        {/* ROOT */}
        {/* ========================================= */}

        <Route
          path="/"
          element={
            <Navigate
              to="/admin"
              replace
            />
          }
        />


        {/* ========================================= */}
        {/* ADMIN */}
        {/* ========================================= */}

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


          {/* FACULTY WEEKLY SCHEDULE */}

          <Route
            path="faculty"
            element={
              <FacultyManagement />
            }
          />


          {/* SUBJECTS */}

          <Route
            path="subjects"
            element={
              <PlaceholderPage
                title="Subject Management"
              />
            }
          />


          {/* PREFERENCES */}

          <Route
            path="preferences"
            element={
              <PlaceholderPage
                title="Faculty Preferences"
              />
            }
          />


          {/* ROOM WEEKLY SCHEDULE */}

          <Route
            path="rooms"
            element={
              <RoomAssignments />
            }
          />


          {/* GENERATE */}

          <Route
            path="generate"
            element={
              <GenerateSchedule />
            }
          />


          {/* COMPLETE GENERATED SCHEDULE */}

          <Route
            path="schedules"
            element={
              <ScheduleView />
            }
          />


          {/* GA ANALYSIS */}

          <Route
            path="analysis"
            element={
              <FitnessAnalysis />
            }
          />

        </Route>


        {/* ========================================= */}
        {/* FACULTY */}
        {/* ========================================= */}

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


        {/* ========================================= */}
        {/* FALLBACK */}
        {/* ========================================= */}

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