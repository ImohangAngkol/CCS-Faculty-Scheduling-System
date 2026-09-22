// ============================================================
// BASELINE
// ============================================================

export type BaselineMode =
  | "fresh"
  | "saved"
  | "uploaded";


export type ResultSource =
  | "generated"
  | "loaded_chromosome";


export type LoadedChromosomeSource =
  | "saved"
  | "uploaded";


// ============================================================
// FITNESS
// ============================================================

export type FitnessBreakdown = {
  subject_preference: number;

  time_preference: number;

  day_preference: number;

  number_of_preparations: number;

  teaching_load_balance: number;

  daily_teaching_load: number;
};


// ============================================================
// GENERATION HISTORY
// ============================================================

export type GAHistoryItem = {
  generation: number;

  best_fitness?: number;

  generation_best_fitness?: number;

  best_ever_fitness?: number;
};


// ============================================================
// SCHEDULE
// ============================================================

export type ScheduleEntry = {
  subject: string;

  title: string;

  type: string;

  day: string;

  start: string;

  end: string;

  section: string;

  faculty: string;

  room: string;
};


// ============================================================
// FACULTY ANALYSIS
// ============================================================

export type FacultyAnalysisItem = {
  Faculty_Code:
    number | string;

  Faculty_Priority:
    number | null;

  Priority_Weight:
    number | null;

  Subject_Satisfaction:
    number | null;

  Day_Satisfaction:
    number | null;

  Time_Satisfaction:
    number | null;

  Preparations:
    number;

  Teaching_Load:
    number;

  Subject_Penalty:
    number;

  Day_Penalty:
    number;

  Time_Penalty:
    number;

  Preparation_Penalty:
    number;

  Total_Penalty:
    number;

  Load_Deviation:
    number | null;

  Absolute_Load_Deviation:
    number | null;
};


// ============================================================
// DAILY FACULTY LOAD
// ============================================================

export type FacultyDailyLoad = {
  Faculty_Code:
    number | string;

  Mon: number;

  Tue: number;

  Wed: number;

  Thu: number;

  Fri: number;

  Sat: number;
};


// ============================================================
// FACULTY ANALYSIS
// ============================================================

export type FacultyAnalysis = {

  faculty:
    FacultyAnalysisItem[];


  daily_load:
    FacultyDailyLoad[];


  summary: {

    total_fitness:
      number;


    average_teaching_load:
      number | null;


    fitness_breakdown:
      FitnessBreakdown;


    professor_analysis: {
      [key: string]:
        number |
        string |
        null |
        undefined;
    };


    parameters: {

      subject_penalty:
        number;

      time_penalty:
        number;

      day_penalty:
        number;

      preparation_penalty:
        number;

      load_balance_penalty:
        number;

      daily_load_penalty:
        number;

      max_preparations:
        number;

      target_teaching_load:
        number;
    };
  };
};


// ============================================================
// GA / CHROMOSOME RESULT
// ============================================================

export type GARunData = {

  best_fitness:
    number;


  fitness_breakdown:
    FitnessBreakdown;


  generations_completed:
    number;


  population_size:
    number;


  history:
    GAHistoryItem[];


  schedule:
    ScheduleEntry[];


  faculty_analysis?:
    FacultyAnalysis;


  // ========================================================
  // BASELINE INFORMATION
  // ========================================================

  baseline_source?:
    BaselineMode | null;


  starting_baseline_fitness?:
    number | null;


  saved_best_updated?:
    boolean;


  saved_best_fitness?:
    number | null;


  // ========================================================
  // LOADED CHROMOSOME INFORMATION
  // ========================================================

  result_source?:
    ResultSource;


  optimization_performed?:
    boolean;


  loaded_chromosome_source?:
    LoadedChromosomeSource;
};


// ============================================================
// API RESPONSE
// ============================================================

export type GARunResponse = {

  status:
    string;

  data:
    GARunData;
};