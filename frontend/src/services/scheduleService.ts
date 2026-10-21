import {z} from "zod";
import {API_BASE, apiClient} from "./apiSession.ts";

const assignment = z.object({
  subject: z.string().min(1), title: z.string().nullable(), section: z.string().min(1),
  type: z.enum(["Lecture", "Laboratory"]), day: z.string().min(1),
  start: z.string().min(1), end: z.string().min(1), room: z.string().nullable(),
}).strict();
const response = z.object({
  schema_version: z.literal(1), availability: z.enum(["available", "empty", "missing"]),
  faculty_id: z.string().uuid(), faculty_code: z.number().int().nonnegative(),
  source: z.object({kind: z.literal("latest_completed_ga_result"), label: z.literal("GA-generated proposal"),
    compatibility: z.enum(["checked_against_loaded_inputs", "not_available"]),
    freshness: z.literal("not_recorded"), saved_at: z.string().datetime({offset: true}).nullable()}).strict(),
  assignments: z.array(assignment),
}).strict();
export type MySchedule = z.infer<typeof response>;

export async function getMySchedule(binding: {faculty_id: string; faculty_code: number}, signal?: AbortSignal): Promise<MySchedule> {
  // No client-selected faculty code/UUID is sent to the server.
  const result = await apiClient.get<unknown>(`${API_BASE}/api/schedules/me`, {signal});
  const parsed = response.safeParse(result.data);
  if (!parsed.success) throw new Error("The timetable response could not be verified. Contact an administrator.");
  const data = parsed.data;
  if (data.faculty_id !== binding.faculty_id || data.faculty_code !== binding.faculty_code
      || (data.availability === "available") !== (data.assignments.length > 0)
      || (data.availability === "missing") !== (data.source.compatibility === "not_available"))
    throw new Error("The timetable does not match your account or source status. No assignments have been displayed.");
  return data;
}
