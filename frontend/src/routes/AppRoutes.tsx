import {
  BrowserRouter,
  Navigate,
  Route,
  Routes,
} from "react-router-dom";

import PreferencesReview
  from "../pages/admin/PreferencesReview";


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
import GenerationHistory from "../pages/admin/GenerationHistory";
import Login from "../pages/Login";
import ProtectedRoute from "./ProtectedRoute";
import {GAProvider} from "../context/GAContext";
import {useAuth} from "../context/AuthContext";
import {accountHome} from "../services/auth";
import Accounts from "../pages/admin/Accounts";
import SubjectManagement from "../pages/admin/SubjectManagement";
import FacultyDashboard from "../pages/faculty/Dashboard";
import FacultyProfile from "../pages/faculty/Profile";
import FacultyMySchedule from "../pages/faculty/MySchedule";


// =============================================
// ADDED: REAL FACULTY PREFERENCES PAGE
// =============================================

import FacultyPreferences
  from "../pages/faculty/Preferences";


export default function AppRoutes() {
  const {user} = useAuth();

  return (

    <BrowserRouter>

      <Routes>
        <Route path="/login" element={<Login />} />

        {/* ROOT */}

        <Route
          path="/"
          element={
            <Navigate
              to={user ? accountHome(user) : "/login"}
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
            <ProtectedRoute role="admin"><GAProvider><AdminLayout /></GAProvider></ProtectedRoute>
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
              <SubjectManagement />
            }
          />


          <Route
            path="preferences"
            element={
              <PreferencesReview 
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
          <Route path="history" element={<GenerationHistory />} />
          <Route path="accounts" element={<Accounts />} />

        </Route>


        {/* ============================================= */}
        {/* FACULTY */}
        {/* ============================================= */}

        <Route
          path="/faculty"
          element={
            <ProtectedRoute role="faculty"><FacultyLayout /></ProtectedRoute>
          }
        >

          <Route
            index
            element={
              <FacultyDashboard />
            }
          />


          {/* ============================================= */}
          {/* CHANGED ONLY THIS ROUTE */}
          {/* ============================================= */}

          <Route
            path="preferences"
            element={
              <FacultyPreferences />
            }
          />


          <Route
            path="schedule"
            element={
              <FacultyMySchedule />
            }
          />


          <Route
            path="profile"
            element={
              <FacultyProfile />
            }
          />

        </Route>


        {/* FALLBACK */}

        <Route
          path="*"
          element={
            <Navigate
              to={user ? accountHome(user) : "/login"}
              replace
            />
          }
        />

      </Routes>

    </BrowserRouter>

  );
}
