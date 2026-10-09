import { DayRecord } from "@/components/DayRecord";
import { FilterBar } from "@/components/FilterBar";
import { formatHrsMins, initials, parseDurationSeconds } from "@/lib/format";
import { loadCalendarInRange, loadDaysInRange, logsDirectory, resolveRange, summarizeRange } from "@/lib/logs";
import { GRACE_MINUTES, MAX_LOGIN_SECONDS, SHIFT_HOURS } from "@/lib/shift";

export const dynamic = "force-dynamic";

export default async function HomePage({
  searchParams,
}: {
  searchParams: Promise<{ start?: string; end?: string }>;
}) {
  const params = await searchParams;
  const range = resolveRange(params.start, params.end);
  const usingDefaultMonth = !params.start && !params.end;
  const days = loadDaysInRange(range.start, range.end);
  const calendar = loadCalendarInRange(range.start, range.end);
  const summary = summarizeRange(days, range.start, range.end);
  const loggedSecs = parseDurationSeconds(summary.logged);
  const workedSecs = parseDurationSeconds(summary.worked);
  const shiftSecs = parseDurationSeconds(summary.shift);
  const overtimeSecs = parseDurationSeconds(summary.overtime);
  const vsShift = workedSecs - shiftSecs;
  const shortOfShift = vsShift < 0;
  const workedVsShift =
    vsShift === 0
      ? "Calculated worked duration matches total shift duration."
      : shortOfShift
        ? `Your calculated worked duration is ${formatHrsMins(Math.abs(vsShift))} less than shift duration.`
        : `Your calculated worked duration is ${formatHrsMins(vsShift)} greater than shift duration.`;

  return (
    <div className="space-y-4">
      <div className="grid min-w-0 gap-4 xl:grid-cols-[minmax(0,1fr)_240px] xl:items-start">
        <FilterBar
          start={range.start}
          end={range.end}
          employee={summary.employeeName}
          username={summary.username}
        />
        <section className="flex min-w-0 items-center gap-3 rounded-2xl border border-line bg-white p-3">
          <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-primary text-sm font-extrabold text-white">
            {initials(summary.employeeName)}
          </div>
          <div className="min-w-0">
            <p className="truncate text-sm font-extrabold text-navy">{summary.employeeName}</p>
            <p className="truncate text-xs text-muted">{summary.employeeRole}</p>
            <p className="text-xs text-muted">{summary.username}</p>
          </div>
        </section>
      </div>

      <p
        className={`rounded-lg border px-4 py-2 text-sm font-semibold ${
          shortOfShift
            ? "border-[#F5C2C7] bg-[#FDECEC] text-[#B42318]"
            : "border-[#BFE8D4] bg-[#E8F8F0] text-[#1B7A4E]"
        }`}
      >
        {workedVsShift}
      </p>
      {overtimeSecs > 0 ? (
        <p className="rounded-lg border border-[#F5C2C7] bg-[#FDECEC] px-4 py-2 text-sm font-semibold text-[#B42318]">
          Login beyond shift + {GRACE_MINUTES} mins grace is not counted ({formatHrsMins(overtimeSecs)} over the daily
          cap).
        </p>
      ) : null}

      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap gap-2">
          <span className="rounded-md bg-[#2F80ED] px-3 py-1.5 text-sm font-bold text-white">
            Present {summary.daysLogged} Days
          </span>
          <span className="rounded-md bg-[#E85D4C] px-3 py-1.5 text-sm font-bold text-white">
            Absent {summary.weekdaysAbsent} Days
          </span>
          <span className="rounded-md border border-line bg-white px-3 py-1.5 text-sm font-semibold text-navy">
            {usingDefaultMonth
              ? `${summary.monthLabel} through ${summary.through}`
              : `${range.start} → ${range.end}`}
          </span>
        </div>
        <a
          href={`/api/export?start=${range.start}&end=${range.end}`}
          className="rounded-lg border border-line bg-white px-4 py-2 text-sm font-semibold text-primary hover:bg-soft"
        >
          Download Report in CSV
        </a>
      </div>

      <section className="grid gap-4 lg:grid-cols-3">
        <div className="rounded-2xl border border-line bg-white lg:col-span-2">
          <div className="rounded-t-2xl bg-[#1E5BB8] px-4 py-2 text-sm font-bold text-white">Worked Hours</div>
          <dl className="divide-y divide-line text-sm">
            <Row label="Days logged" value={`${summary.daysLogged} Days`} />
            <Row
              label={`Total shift duration (${SHIFT_HOURS} Hrs / day)`}
              value={formatHrsMins(shiftSecs)}
            />
            <Row
              label={`Allowed login (shift + ${GRACE_MINUTES} mins grace / day)`}
              value={formatHrsMins(summary.daysLogged * MAX_LOGIN_SECONDS)}
            />
            <Row label="Total logged in duration (counted)" value={formatHrsMins(loggedSecs)} />
            {overtimeSecs > 0 ? (
              <Row label="Over daily cap (not counted)" value={formatHrsMins(overtimeSecs)} />
            ) : null}
            <Row label="Total break duration" value={formatHrsMins(parseDurationSeconds(summary.breaks))} />
            <Row
              label="Productive breaks (Meeting, Lunch, Prayer, Tea, Call)"
              value={formatHrsMins(parseDurationSeconds(summary.productiveBreaks))}
            />
            <Row
              label="Non-productive breaks (Logout, Idle, Absence)"
              value={formatHrsMins(parseDurationSeconds(summary.nonProductiveBreaks))}
            />
            <Row label="Daily gross duration" value={formatHrsMins(loggedSecs)} />
            <Row label="Calculated worked hours" value={formatHrsMins(workedSecs)} strong />
            <Row label="Shift notes" value={String(summary.notes)} />
          </dl>
        </div>
        <div className="rounded-2xl border border-line bg-white">
          <div className="rounded-t-2xl bg-[#1E5BB8] px-4 py-2 text-sm font-bold text-white">
            Attendance record
          </div>
          <dl className="divide-y divide-line text-sm">
            <Row label="Range start" value={range.start} />
            <Row label="Counted through" value={summary.through} />
            <Row label="Weekdays so far" value={String(summary.weekdays)} />
            <Row label="Days with logs" value={String(summary.daysLogged)} />
            <Row label="Absent weekdays" value={String(summary.weekdaysAbsent)} />
            <Row label="Off days (weekends)" value={String(summary.offDays)} />
          </dl>
          <p className="px-4 py-3 text-xs text-muted">
            Absent only counts weekdays up to today. Saturdays and Sundays are off days, unless you logged a shift.
          </p>
        </div>
      </section>

      {calendar.length === 0 ? (
        <section className="rounded-2xl border border-dashed border-line bg-white p-10 text-center">
          <h2 className="text-lg font-bold text-navy">No attendance in this range</h2>
          <p className="mt-2 text-sm text-muted">
            FaceLES writes a JSON file per day in{" "}
            <code className="rounded bg-soft px-1.5 py-0.5 text-navy">{logsDirectory()}</code>
          </p>
        </section>
      ) : (
        <section className="overflow-hidden rounded-2xl border border-line">
          <div className="hidden grid-cols-12 bg-[#1E5BB8] px-4 py-2 text-xs font-bold uppercase tracking-wide text-white md:grid">
            <span className="col-span-2">Dates</span>
            <span className="col-span-3">Timing info</span>
            <span className="col-span-5">Breaks info</span>
            <span className="col-span-2">Shift info</span>
          </div>
          {calendar.map((row) => (
            <DayRecord key={row.date} row={row} start={range.start} end={range.end} />
          ))}
        </section>
      )}
    </div>
  );
}

function Row({
  label,
  value,
  strong,
}: {
  label: string;
  value: string;
  strong?: boolean;
}) {
  return (
    <div className="flex items-center justify-between gap-4 px-4 py-2.5">
      <dt className="text-muted">{label}</dt>
      <dd className={`tabular-nums ${strong ? "font-extrabold text-navy" : "font-semibold text-navy"}`}>{value}</dd>
    </div>
  );
}
