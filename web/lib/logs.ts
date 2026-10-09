import fs from "fs";
import path from "path";
import {
  clampRangeEnd,
  eachIsoDate,
  formatDayLabel,
  formatSeconds,
  isProductiveBreak,
  isWeekday,
  monthBounds,
  parseDurationSeconds,
} from "./format";
import type { CalendarDay, DayShift, RangeSummary, RawDayLog, RawSession, Shift } from "./types";

const DEFAULT_NAME = process.env.FACELES_EMPLOYEE_NAME || "Saleet Ul Hassan";
const DEFAULT_ROLE = process.env.FACELES_EMPLOYEE_ROLE || "Employee · Face-verified attendance";

export function logsDirectory(): string {
  if (process.env.FACELES_LOGS_DIR) return process.env.FACELES_LOGS_DIR;
  const fromWeb = path.resolve(process.cwd(), "..", "attendance_logs");
  const fromRoot = path.resolve(process.cwd(), "attendance_logs");
  if (fs.existsSync(fromWeb)) return fromWeb;
  return fromRoot;
}

function uniqueBreaks(session: RawSession) {
  const seen = new Set<string>();
  const rows: Shift["breaks"] = [];
  for (const item of session.breaks || []) {
    if (!Array.isArray(item) || item.length < 3) continue;
    const start = String(item[0] ?? "");
    const end = String(item[1] ?? "");
    const duration = String(item[2] ?? "").split(".")[0];
    const reason = String(item[3] ?? "Break");
    const key = `${start}|${end}|${reason}`;
    if (seen.has(key)) continue;
    seen.add(key);
    rows.push({
      start,
      end,
      duration,
      reason,
      productive: isProductiveBreak(reason),
    });
  }
  return rows;
}

function toShift(session: RawSession, dayNote: string): Shift {
  return {
    loginTime: session.login_time || "--",
    logoutTime: session.logout_time || "--",
    onShift: String(session.login_duration || "0:00:00").split(".")[0],
    worked: String(session.work_duration || "0:00:00").split(".")[0],
    breaksTotal: String(session.total_break_time || "0:00:00").split(".")[0],
    note: (session.shift_note || dayNote || "").trim(),
    employeeName: session.employee_name || DEFAULT_NAME,
    employeeRole: session.employee_role || DEFAULT_ROLE,
    username: session.username || session.user || "",
    hostname: session.hostname || "",
    ip: session.ip_address || "",
    platform: session.platform || "",
    breaks: uniqueBreaks(session),
  };
}

function canonicalShifts(sessions: RawSession[], dayNote: string): Shift[] {
  // FaceLES appends a full snapshot on every logout. Keep the latest row
  // for each login time so the dashboard shows one shift, not duplicates.
  const latest = new Map<string, RawSession>();
  for (const session of sessions) {
    const key = session.login_time || `anon-${latest.size}`;
    latest.set(key, session);
  }
  return [...latest.values()].map((session) => toShift(session, dayNote));
}

function breakBuckets(shifts: Shift[]) {
  let productive = 0;
  let nonProductive = 0;
  for (const shift of shifts) {
    for (const row of shift.breaks) {
      const secs = parseDurationSeconds(row.duration);
      if (row.productive) productive += secs;
      else nonProductive += secs;
    }
  }
  return { productive, nonProductive };
}

function summarize(shifts: Shift[]) {
  const worked = shifts.reduce((sum, s) => sum + parseDurationSeconds(s.worked), 0);
  const breaks = shifts.reduce((sum, s) => sum + parseDurationSeconds(s.breaksTotal), 0);
  const onShift = shifts.reduce((sum, s) => sum + parseDurationSeconds(s.onShift), 0);
  const breakCount = shifts.reduce((sum, s) => sum + s.breaks.length, 0);
  const buckets = breakBuckets(shifts);
  return {
    worked: formatSeconds(worked),
    breaks: formatSeconds(breaks),
    onShift: formatSeconds(onShift),
    breakCount,
    productiveBreaks: formatSeconds(buckets.productive),
    nonProductiveBreaks: formatSeconds(buckets.nonProductive),
  };
}

export function loadDay(iso: string): DayShift | null {
  const file = path.join(logsDirectory(), `${iso}.json`);
  if (!fs.existsSync(file)) return null;
  try {
    const data = JSON.parse(fs.readFileSync(file, "utf8")) as RawDayLog;
    const date = data.date || iso;
    const { label, weekday } = formatDayLabel(date);
    const note = (data.shift_note || "").trim();
    const shifts = canonicalShifts(data.sessions || [], note);
    const employee = shifts[0];
    return {
      date,
      label,
      weekday,
      note: note || employee?.note || "",
      employeeName: employee?.employeeName || DEFAULT_NAME,
      employeeRole: employee?.employeeRole || DEFAULT_ROLE,
      shifts,
      totals: summarize(shifts),
    };
  } catch {
    return null;
  }
}

export function loadAllDays(): DayShift[] {
  const dir = logsDirectory();
  if (!fs.existsSync(dir)) return [];
  return fs
    .readdirSync(dir)
    .filter((name) => /^\d{4}-\d{2}-\d{2}\.json$/.test(name))
    .map((name) => name.replace(/\.json$/, ""))
    .sort((a, b) => b.localeCompare(a))
    .map((iso) => loadDay(iso))
    .filter((day): day is DayShift => day !== null);
}

export function resolveRange(start?: string, end?: string): { start: string; end: string; label: string } {
  const month = monthBounds();
  const s = start && /^\d{4}-\d{2}-\d{2}$/.test(start) ? start : month.start;
  const e = end && /^\d{4}-\d{2}-\d{2}$/.test(end) ? end : month.end;
  return { start: s <= e ? s : e, end: s <= e ? e : s, label: month.label };
}

export function loadDaysInRange(start: string, end: string): DayShift[] {
  return loadAllDays().filter((day) => day.date >= start && day.date <= end);
}

export function summarizeRange(days: DayShift[], start: string, end: string): RangeSummary {
  const latest = days[0];
  const worked = days.reduce((sum, d) => sum + parseDurationSeconds(d.totals.worked), 0);
  const logged = days.reduce((sum, d) => sum + parseDurationSeconds(d.totals.onShift), 0);
  const breaks = days.reduce((sum, d) => sum + parseDurationSeconds(d.totals.breaks), 0);
  const productive = days.reduce((sum, d) => sum + parseDurationSeconds(d.totals.productiveBreaks), 0);
  const nonProductive = days.reduce((sum, d) => sum + parseDurationSeconds(d.totals.nonProductiveBreaks), 0);
  const through = clampRangeEnd(start, end);
  const elapsed = eachIsoDate(start, through);
  const weekdays = elapsed.filter(isWeekday);
  const loggedDates = new Set(days.map((day) => day.date));
  return {
    start,
    end,
    through,
    monthLabel: monthBounds(new Date(`${start}T12:00:00`)).label,
    daysLogged: days.length,
    weekdays: weekdays.length,
    weekdaysAbsent: weekdays.filter((iso) => !loggedDates.has(iso)).length,
    offDays: elapsed.filter((iso) => !isWeekday(iso) && !loggedDates.has(iso)).length,
    employeeName: latest?.employeeName || DEFAULT_NAME,
    employeeRole: latest?.employeeRole || DEFAULT_ROLE,
    username: latest?.shifts[0]?.username || "saleet",
    logged: formatSeconds(logged),
    worked: formatSeconds(worked),
    breaks: formatSeconds(breaks),
    productiveBreaks: formatSeconds(productive),
    nonProductiveBreaks: formatSeconds(nonProductive),
    notes: days.filter((d) => d.note).length,
  };
}

export function loadCalendarInRange(start: string, end: string): CalendarDay[] {
  const through = clampRangeEnd(start, end);
  const logs = new Map(loadDaysInRange(start, through).map((day) => [day.date, day]));
  return eachIsoDate(start, through)
    .reverse()
    .map((iso) => {
      const { weekday } = formatDayLabel(iso);
      const day = logs.get(iso);
      if (day) return { date: iso, weekday, kind: "worked" as const, day };
      if (!isWeekday(iso)) return { date: iso, weekday, kind: "off" as const };
      return { date: iso, weekday, kind: "absent" as const };
    });
}
