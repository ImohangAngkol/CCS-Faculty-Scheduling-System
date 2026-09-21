import {
  BrowserRouter,
  Routes,
  Route,
  Navigate,
} from "react-router-dom";

import AdminLayout from "../layouts/AdminLayout";
import FacultyLayout from "../layouts/FacultyLayout";

import AdminDashboard from "../pages/admin/Dashboard";
import GenerateSchedule from "../pages/admin/GenerateSchedule";
import ScheduleView from "../pages/admin/ScheduleView";
import FitnessAnalysis from "../pages/admin/FitnessAnalysis";


function FacultyDashboard() {
  return <div>Faculty Dashboard</div>;
}


function PlaceholderPage({
  title,
}: {
  title: string;
}) {
  return (
    <div className="rounded-xl border bg-white p-6">
      <h1 className="text-2xl font-bold text-slate-900">
        {title}
      </h1>

      <p className="mt-2 text-slate-500">
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
          element={<AdminLayout />}
        >

          {/* DASHBOARD */}
          <Route
            index
            element={<AdminDashboard />}
          />


          {/* FACULTY MANAGEMENT */}
          <Route
            path="faculty"
            element={
              <PlaceholderPage
                title="Faculty Management"
              />
            }
          />


          {/* SUBJECT MANAGEMENT */}
          <Route
            path="subjects"
            element={
              <PlaceholderPage
                title="Subject Management"
              />
            }
          />


          {/* PREFERENCES REVIEW */}
          <Route
            path="preferences"
            element={
              <PlaceholderPage
                title="Faculty Preferences"
              />
            }
          />


          {/* GENERATE SCHEDULE */}
          <Route
            path="generate"
            element={<GenerateSchedule />}
          />


          {/* GENERATED SCHEDULE */}
          <Route
            path="schedules"
            element={<ScheduleView />}
          />


          {/* GA ANALYSIS */}
          <Route
            path="analysis"
            element={<FitnessAnalysis />}
          />

        </Route>


        {/* ========================================= */}
        {/* FACULTY */}
        {/* ========================================= */}

        <Route
          path="/faculty"
          element={<FacultyLayout />}
        >

          {/* FACULTY DASHBOARD */}
          <Route
            index
            element={<FacultyDashboard />}
          />


          {/* MY PREFERENCES */}
          <Route
            path="preferences"
            element={
              <PlaceholderPage
                title="My Preferences"
              />
            }
          />


          {/* MY SCHEDULE */}
          <Route
            path="schedule"
            element={
              <PlaceholderPage
                title="My Schedule"
              />
            }
          />


          {/* PROFILE */}
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