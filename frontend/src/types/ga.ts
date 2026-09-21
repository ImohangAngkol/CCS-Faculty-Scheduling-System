export type FitnessBreakdown = {
  subject_preference: number;
  time_preference: number;
  day_preference: number;
  number_of_preparations: number;
  teaching_load_balance: number;
  daily_teaching_load: number;
};

export type GAHistoryItem = {
  generation: number;
  best_fitness?: number;
  generation_best_fitness?: number;
  best_ever_fitness?: number;
};

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

export type GARunData = {
  best_fitness: number;
  fitness_breakdown: FitnessBreakdown;
  generations_completed: number;
  population_size: number;
  history: GAHistoryItem[];
  schedule: ScheduleEntry[];
};

export type GARunResponse = {
  status: string;
  data: GARunData;
};