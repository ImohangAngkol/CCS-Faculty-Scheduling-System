import type { GAExecutionStatus } from "./gaMonitoring";

export type RunLogEntry = { sequence: number; timestamp: string; message: string; line_truncated: boolean };
export type RunLogs = {
  run_id: string; process_instance_id: string; log_epoch: string;
  state: GAExecutionStatus; execution_active: boolean; entries: RunLogEntry[];
  latest_sequence: number; next_sequence: number; has_more: boolean;
  earlier_logs_truncated: boolean; cursor_reset: boolean;
};
export type LogHistory = { epoch: string | null; cursor: number; entries: RunLogEntry[]; truncated: boolean };
export const emptyLogHistory = (): LogHistory => ({ epoch: null, cursor: 0, entries: [], truncated: false });

export function needsLogReplay(history: LogHistory, page: RunLogs): boolean {
  return history.epoch !== null && history.epoch !== page.log_epoch && !page.cursor_reset;
}

export function validateRunLogs(value: RunLogs, runId: string, processId: string): RunLogs {
  const states = ["CREATED", "INITIALIZING", "RUNNING", "PAUSE_REQUESTED", "PAUSING", "PAUSED", "RESUMING", "STOP_REQUESTED", "STOPPING", "STOPPED", "COMPLETED", "FAILED", "INTERRUPTED"];
  const invalid = () => { throw new Error("Run log response has invalid ordering, metrics or identity. Verify the backend instance and refresh to reconnect."); };
  if (!value || value.run_id !== runId || value.process_instance_id !== processId
      || typeof value.log_epoch !== "string" || !value.log_epoch || !states.includes(value.state)
      || ![value.execution_active, value.has_more, value.earlier_logs_truncated, value.cursor_reset].every(item => typeof item === "boolean")
      || ![value.latest_sequence, value.next_sequence].every(item => Number.isSafeInteger(item) && item >= 0)
      || value.next_sequence > value.latest_sequence || value.has_more !== (value.next_sequence < value.latest_sequence)
      || !Array.isArray(value.entries) || value.entries.length > 200) invalid();
  let previous = 0;
  for (const entry of value.entries) {
    if (!entry || !Number.isSafeInteger(entry.sequence) || entry.sequence <= previous
        || entry.sequence > value.latest_sequence || typeof entry.message !== "string" || entry.message.length > 4096
        || typeof entry.timestamp !== "string" || !Number.isFinite(Date.parse(entry.timestamp))
        || typeof entry.line_truncated !== "boolean") invalid();
    previous = entry.sequence;
  }
  if (value.entries.length && previous !== value.next_sequence) invalid();
  return value;
}

/** A new buffer epoch means earlier diagnostics are unavailable, not a new GA run. */
export function mergeRunLogs(history: LogHistory, page: RunLogs): LogHistory {
  const changed = history.epoch !== null && history.epoch !== page.log_epoch;
  const reset = changed || page.cursor_reset;
  const existing = reset ? [] : history.entries;
  const cursor = reset ? 0 : history.cursor;
  return {
    epoch: page.log_epoch,
    cursor: Math.max(cursor, page.next_sequence),
    entries: [...existing, ...page.entries.filter(entry => entry.sequence > cursor)].slice(-500),
    truncated: history.truncated || page.earlier_logs_truncated || reset,
  };
}

export function logPollDelay(page: RunLogs): number | null {
  if (page.has_more) return 250;
  if (!page.execution_active && ["STOPPED", "COMPLETED", "FAILED", "INTERRUPTED"].includes(page.state)) return null;
  return page.state === "PAUSED" && !page.execution_active ? 5000 : 1000;
}
