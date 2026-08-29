import { useState, type ReactNode } from "react";
import {
  AlertTriangle,
  BarChart3,
  BookOpen,
  Building2,
  CalendarDays,
  ChevronDown,
  Clock3,
  Download,
  FileBarChart,
  FileText,
  GraduationCap,
  Heart,
  LayoutDashboard,
  Menu,
  Printer,
  Settings,
  SlidersHorizontal,
  User,
  Users,
  WandSparkles,
  X,
} from "lucide-react";



const days = [
  "Monday",
  "Tuesday",
  "Wednesday",
  "Thursday",
  "Friday",
  "Saturday",
];

const timeSlots = [
  "7:00 AM",
  "8:00 AM",
  "9:00 AM",
  "10:00 AM",
  "11:00 AM",
  "12:00 PM",
  "1:00 PM",
  "2:00 PM",
  "3:00 PM",
  "4:00 PM",
  "5:00 PM",
  "6:00 PM",
  "7:00 PM",
];

/* =========================================================
   SIDEBAR ITEM
========================================================= */

function SidebarItem({
  icon,
  label,
  active = false,
}: {
  icon: ReactNode;
  label: string;
  active?: boolean;
}) {
  return (
    <button
      className={`flex w-full items-center gap-3 rounded-lg px-4 py-2.5 text-left text-sm transition ${
        active
          ? "bg-[#7A0019] font-semibold text-white shadow-sm"
          : "text-gray-700 hover:bg-[#FFF6D8] hover:text-[#7A0019]"
      }`}
    >
      {icon}

      <span>{label}</span>
    </button>
  );
}

/* =========================================================
   LEGEND
========================================================= */

function Legend({
  color,
  label,
}: {
  color: string;
  label: string;
}) {
  return (
    <div className="flex items-center gap-2">
      <span className={`h-3 w-3 rounded-full ${color}`} />

      <span>{label}</span>
    </div>
  );
}

/* =========================================================
   MAIN APP
========================================================= */

function App() {
  const [sidebarOpen, setSidebarOpen] = useState(true);

  const [showProfessors, setShowProfessors] =
    useState(true);

  const [showRooms, setShowRooms] = useState(false);

  const [showCourses, setShowCourses] = useState(false);

  return (
    <div className="min-h-screen bg-[#F8F8F7] text-[#1F1F1F]">

      {/* =====================================================
          TOP HEADER
      ====================================================== */}

      <header className="fixed left-0 right-0 top-0 z-30 flex h-[74px] items-center justify-between border-b border-gray-200 bg-white px-6">

        {/* BRAND */}
        <div className="flex items-center gap-4">

          {/* SIDEBAR TOGGLE */}
          <button
            onClick={() =>
              setSidebarOpen(!sidebarOpen)
            }
            className="rounded-lg p-2 text-gray-600 hover:bg-gray-100 hover:text-[#7A0019]"
            aria-label="Toggle sidebar"
          >
            {sidebarOpen ? (
              <X size={20} />
            ) : (
              <Menu size={20} />
            )}
          </button>

          {/* LOGO + TITLE */}
          <div className="flex items-center gap-3">

            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-[#7A0019] text-white shadow-sm">
              <GraduationCap size={24} />
            </div>

            <div>
              <h1 className="text-lg font-bold text-[#7A0019]">
                CCS Scheduler
              </h1>

              <p className="text-xs text-gray-500">
                Faculty Scheduling System
              </p>
            </div>

          </div>
        </div>

        {/* HEADER ACTIONS */}
        <div className="flex items-center gap-3">

          {/* SEMESTER */}
          <button className="flex items-center gap-3 rounded-lg border border-gray-300 bg-white px-4 py-2.5 text-sm hover:border-[#7A0019]">

            <CalendarDays
              size={18}
              className="text-[#7A0019]"
            />

            <span className="text-gray-600">
              Select Semester
            </span>

            <ChevronDown size={16} />
          </button>

          {/* EXPORT */}
          <button className="flex items-center gap-2 rounded-lg border border-[#7A0019] px-4 py-2.5 text-sm font-medium text-[#7A0019] hover:bg-[#FFF6D8]">

            <Download size={17} />

            EXPORT SCHEDULE
          </button>

          {/* PRINT */}
          <button className="flex items-center gap-2 rounded-lg border border-[#7A0019] px-4 py-2.5 text-sm font-medium text-[#7A0019] hover:bg-[#FFF6D8]">

            <Printer size={17} />

            PRINT SCHEDULE
          </button>

          {/* USER */}
          <div className="ml-3 flex items-center gap-2">

            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-[#FFF6D8] text-[#7A0019]">
              <User size={20} />
            </div>

            <div className="hidden text-xs md:block">

              <p className="font-medium">
                Administrator
              </p>

              <p className="text-gray-500">
                Account
              </p>

            </div>

            <ChevronDown size={15} />
          </div>

        </div>
      </header>

      {/* =====================================================
          SIDEBAR
      ====================================================== */}

      {sidebarOpen && (
        <aside className="fixed bottom-0 left-0 top-[74px] z-20 w-[240px] overflow-y-auto border-r border-gray-200 bg-white px-3 py-5">

          {/* CURRENT FILE */}
          <div className="mb-6 px-3">

            <div className="mb-2 flex items-center gap-2 text-sm font-semibold text-[#7A0019]">

              <FileText size={18} />

              Current File

            </div>

            <div className="rounded-lg border border-gray-200 bg-white p-3">

              <p className="text-xs font-medium text-gray-600">
                No file selected
              </p>

              <p className="mt-1 text-[11px] text-gray-400">
                Import a schedule file to begin.
              </p>

              <button className="mt-3 w-full rounded-md bg-[#7A0019] py-2 text-xs font-semibold text-white hover:bg-[#5C0013]">

                IMPORT NEW CSV

              </button>

            </div>
          </div>

          {/* NAVIGATION */}
          <nav className="space-y-1">

            {/* DASHBOARD */}

            <SidebarItem
              icon={<LayoutDashboard size={19} />}
              label="Dashboard"
            />

            {/* MANAGE */}

            <p className="px-3 pb-1 pt-5 text-[11px] font-semibold uppercase tracking-wide text-gray-500">
              Manage
            </p>

            <SidebarItem
              icon={<Users size={19} />}
              label="Faculty"
            />

            <SidebarItem
              icon={<BookOpen size={19} />}
              label="Courses"
            />

            <SidebarItem
              icon={<Building2 size={19} />}
              label="Rooms"
            />

            <SidebarItem
              icon={<Clock3 size={19} />}
              label="Time Slots"
            />

            <SidebarItem
              icon={<Heart size={19} />}
              label="Preferences"
            />

            {/* SCHEDULING */}

            <p className="px-3 pb-1 pt-5 text-[11px] font-semibold uppercase tracking-wide text-gray-500">
              Scheduling
            </p>

            <SidebarItem
              icon={<WandSparkles size={19} />}
              label="Generate Schedule"
            />

            <SidebarItem
              icon={<CalendarDays size={19} />}
              label="View Schedule"
              active
            />

            <SidebarItem
              icon={<AlertTriangle size={19} />}
              label="Conflicts"
            />

            {/* REPORTS */}

            <p className="px-3 pb-1 pt-5 text-[11px] font-semibold uppercase tracking-wide text-gray-500">
              Reports
            </p>

            <SidebarItem
              icon={<FileBarChart size={19} />}
              label="Workload Report"
            />

            <SidebarItem
              icon={<FileText size={19} />}
              label="Schedule Report"
            />

            <SidebarItem
              icon={<BarChart3 size={19} />}
              label="GA Performance"
            />

            {/* SETTINGS */}

            <p className="px-3 pb-1 pt-5 text-[11px] font-semibold uppercase tracking-wide text-gray-500">
              Settings
            </p>

            <SidebarItem
              icon={<Settings size={19} />}
              label="GA Configuration"
            />

            <SidebarItem
              icon={<SlidersHorizontal size={19} />}
              label="System Settings"
            />

            <SidebarItem
              icon={<User size={19} />}
              label="Users"
            />

          </nav>
        </aside>
      )}

      {/* =====================================================
          MAIN CONTENT
      ====================================================== */}

      <main
        className={`pt-[74px] transition-all ${
          sidebarOpen ? "ml-[240px]" : "ml-0"
        }`}
      >

        <div className="p-6">

          {/* =================================================
              PAGE HEADER
          ================================================== */}

          <div className="mb-5 flex items-center justify-between">

            <div className="flex items-center gap-3">

              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-[#FFF6D8] text-[#7A0019]">

                <CalendarDays size={22} />

              </div>

              <div>

                <h2 className="text-2xl font-bold text-[#7A0019]">
                  Academic Schedule
                </h2>

                <p className="text-sm text-gray-500">
                  Faculty scheduling and workload overview
                </p>

              </div>

            </div>

            {/* GENERATE BUTTON */}

            <button className="flex items-center gap-2 rounded-lg bg-[#F2B705] px-4 py-2.5 text-sm font-bold text-[#5C0013] shadow-sm hover:bg-[#DCA600]">

              <WandSparkles size={18} />

              GENERATE SCHEDULE

            </button>

          </div>

          {/* =================================================
              MAIN WORK AREA
          ================================================== */}

          <div className="grid grid-cols-[250px_minmax(0,1fr)] gap-4">

            {/* =================================================
                FILTER PANEL
            ================================================== */}

            <section className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">

              {/* TITLE */}

              <div className="mb-4">

                <label className="mb-2 block text-xs font-semibold text-gray-600">
                  TITLE
                </label>

                <input
                  type="text"
                  placeholder="Enter schedule title"
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm outline-none focus:border-[#7A0019] focus:ring-1 focus:ring-[#7A0019]"
                />

              </div>

              {/* SELECT SCHEDULE */}

              <div className="rounded-xl border border-gray-200">

                {/* HEADER */}

                <div className="border-b border-gray-200 p-4">

                  <div className="flex items-center justify-between">

                    <h3 className="text-sm font-bold uppercase text-gray-700">
                      Select Schedule
                    </h3>

                    <button className="text-xs font-medium text-gray-500 hover:text-[#7A0019]">
                      RESET FILTERS
                    </button>

                  </div>

                </div>

                {/* =================================================
                    PROFESSORS
                ================================================== */}

                <div>

                  <button
                    onClick={() =>
                      setShowProfessors(
                        !showProfessors,
                      )
                    }
                    className="flex w-full items-center justify-between border-b border-gray-200 px-4 py-3 text-sm font-semibold text-[#7A0019]"
                  >

                    PROFESSORS

                    <ChevronDown
                      size={16}
                      className={`transition ${
                        showProfessors
                          ? "rotate-180"
                          : ""
                      }`}
                    />

                  </button>

                  {showProfessors && (
                    <div className="p-3">

                      <input
                        type="text"
                        placeholder="Search professors..."
                        className="mb-3 w-full rounded-lg border border-gray-300 px-3 py-2 text-xs outline-none focus:border-[#7A0019]"
                      />

                      <div className="py-5 text-center">

                        <Users
                          size={26}
                          className="mx-auto mb-2 text-gray-300"
                        />

                        <p className="text-xs text-gray-400">
                          No professors loaded.
                        </p>

                        <p className="mt-1 text-[11px] text-gray-300">
                          Faculty data will appear here.
                        </p>

                      </div>

                    </div>
                  )}

                </div>

                {/* =================================================
                    ROOMS
                ================================================== */}

                <div>

                  <button
                    onClick={() =>
                      setShowRooms(!showRooms)
                    }
                    className="flex w-full items-center justify-between border-t border-gray-200 px-4 py-4 text-sm font-semibold text-[#7A0019]"
                  >

                    ROOMS

                    <ChevronDown
                      size={16}
                      className={`transition ${
                        showRooms
                          ? "rotate-180"
                          : ""
                      }`}
                    />

                  </button>

                  {showRooms && (
                    <div className="border-t border-gray-100 p-4 text-center">

                      <Building2
                        size={24}
                        className="mx-auto mb-2 text-gray-300"
                      />

                      <p className="text-xs text-gray-400">
                        No rooms loaded.
                      </p>

                    </div>
                  )}

                </div>

                {/* =================================================
                    COURSES
                ================================================== */}

                <div>

                  <button
                    onClick={() =>
                      setShowCourses(
                        !showCourses,
                      )
                    }
                    className="flex w-full items-center justify-between border-t border-gray-200 px-4 py-4 text-sm font-semibold text-[#7A0019]"
                  >

                    COURSES

                    <ChevronDown
                      size={16}
                      className={`transition ${
                        showCourses
                          ? "rotate-180"
                          : ""
                      }`}
                    />

                  </button>

                  {showCourses && (
                    <div className="border-t border-gray-100 p-4 text-center">

                      <BookOpen
                        size={24}
                        className="mx-auto mb-2 text-gray-300"
                      />

                      <p className="text-xs text-gray-400">
                        No courses loaded.
                      </p>

                    </div>
                  )}

                </div>

              </div>

              {/* =================================================
                  ACTION BUTTONS
              ================================================== */}

              <div className="mt-4 space-y-2">

                <button className="flex w-full items-center justify-center gap-2 rounded-lg bg-[#7A0019] py-2.5 text-sm font-semibold text-white hover:bg-[#5C0013]">

                  <Settings size={17} />

                  EDIT SCHEDULES

                </button>

                <button className="flex w-full items-center justify-center gap-2 rounded-lg border border-[#7A0019] py-2.5 text-sm font-semibold text-[#7A0019] hover:bg-[#FFF6D8]">

                  <span className="text-lg">+</span>

                  ADD CUSTOM SCHEDULE

                </button>

              </div>

            </section>

            {/* =================================================
                CALENDAR
            ================================================== */}

            <section className="min-w-0 rounded-xl border border-gray-200 bg-white p-3 shadow-sm">

              <div className="overflow-x-auto rounded-lg border border-gray-200">

                {/* DAYS */}

                <div className="grid min-w-[850px] grid-cols-[70px_repeat(6,minmax(100px,1fr))] border-b border-gray-200">

                  {/* EMPTY TIME HEADER */}

                  <div className="border-r border-gray-200 bg-gray-50 p-3" />

                  {/* DAYS */}

                  {days.map((day) => (
                    <div
                      key={day}
                      className="border-r border-gray-200 bg-gray-50 p-3 text-center text-sm font-semibold text-gray-700 last:border-r-0"
                    >
                      {day}
                    </div>
                  ))}

                </div>

                {/* =================================================
                    TIME GRID
                ================================================== */}

                <div className="min-w-[850px]">

                  {timeSlots.map((time) => (

                    <div
                      key={time}
                      className="grid min-h-[65px] grid-cols-[70px_repeat(6,minmax(100px,1fr))] border-b border-gray-100 last:border-b-0"
                    >

                      {/* TIME */}

                      <div className="border-r border-gray-200 bg-gray-50 px-3 pt-2 text-xs font-medium text-gray-600">
                        {time}
                      </div>

                      {/* EMPTY CELLS */}

                      {days.map((day) => (

                        <div
                          key={`${day}-${time}`}
                          className="border-r border-gray-100 last:border-r-0 hover:bg-[#FFFDF3]"
                        />

                      ))}

                    </div>

                  ))}

                </div>

              </div>

              {/* =================================================
                  EMPTY STATE
              ================================================== */}

              <div className="flex flex-col items-center justify-center py-10">

                <div className="mb-3 flex h-14 w-14 items-center justify-center rounded-full bg-[#FFF6D8] text-[#7A0019]">

                  <CalendarDays size={28} />

                </div>

                <h3 className="text-sm font-semibold text-gray-600">
                  No schedule generated
                </h3>

                <p className="mt-1 max-w-md text-center text-xs text-gray-400">
                  Select scheduling data or generate a
                  schedule to view faculty timeblocks.
                </p>

              </div>

              {/* =================================================
                  LEGEND
              ================================================== */}

              <div className="flex flex-wrap items-center gap-5 rounded-lg border border-gray-200 px-4 py-3 text-xs">

                <Legend
                  color="bg-blue-500"
                  label="Lecture"
                />

                <Legend
                  color="bg-green-600"
                  label="Laboratory"
                />

                <Legend
                  color="bg-yellow-500"
                  label="Office Hours"
                />

                <Legend
                  color="bg-purple-500"
                  label="Hybrid"
                />

                <Legend
                  color="bg-red-500"
                  label="Special Class"
                />

                {/* SUMMARY */}

                <div className="ml-auto flex flex-wrap gap-5 font-medium text-gray-400">

                  <span>
                    Total Units: —
                  </span>

                  <span>
                    Total Classes: —
                  </span>

                  <span>
                    Free Time: —
                  </span>

                </div>

              </div>

            </section>

          </div>

        </div>

      </main>

    </div>
  );
}

export default App;