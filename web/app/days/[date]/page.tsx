import Link from "next/link";
import { notFound } from "next/navigation";
import { BreakTable } from "@/components/BreakTable";
import { Stat } from "@/components/Stat";
import { initials } from "@/lib/format";
import { loadDay } from "@/lib/logs";

export const dynamic = "force-dynamic";

export default async function DayPage({
  params,
  searchParams,
}: {
  params: Promise<{ date: string }>;
  searchParams: Promise<{ start?: string; end?: string }>;
}) {
  const { date } = await params;
  const query = await searchParams;
  const day = loadDay(date);
  if (!day) notFound();
  const shift = day.shifts[0];
  const back =
    query.start && query.end ? `/?start=${query.start}&end=${query.end}` : "/";

  return (
    <div className="space-y-6">
      <Link href={back} className="text-sm font-semibold text-primary hover:underline">
        ← Attendance range
      </Link>

      <section className="flex flex-col gap-5 rounded-3xl border border-line bg-white p-6 shadow-sm md:flex-row md:items-center md:justify-between">
        <div className="flex items-center gap-4">
          <div className="flex h-16 w-16 items-center justify-center rounded-full bg-primary text-xl font-extrabold text-white">
            {initials(day.employeeName)}
          </div>
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-muted">{day.weekday}</p>
            <h1 className="text-2xl font-extrabold text-navy">{day.label}</h1>
            <p className="text-sm text-muted">
              {day.employeeName}
              {shift?.username ? ` · ${shift.username}` : ""}
            </p>
            <p className="text-sm text-muted">{day.employeeRole}</p>
          </div>
        </div>
        <p className="text-sm text-muted">
          {shift?.hostname || "Local machine"}
          {shift?.ip ? ` · ${shift.ip}` : ""}
        </p>
      </section>

      <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Stat label="Login" value={shift?.loginTime || "--"} tone="primary" />
        <Stat label="Logout" value={shift?.logoutTime || "--"} />
        <Stat label="Worked" value={day.totals.worked} tone="purple" />
        <Stat label="Breaks" value={day.totals.breaks} tone="orange" />
      </section>

      {day.note ? (
        <section className="rounded-3xl border border-line bg-white p-5">
          <p className="text-xs font-semibold uppercase tracking-wide text-muted">Shift note</p>
          <p className="mt-2 text-navy">{day.note}</p>
        </section>
      ) : null}

      {day.shifts.map((item, index) => (
        <section key={`${item.loginTime}-${index}`} className="space-y-4 rounded-3xl border border-line bg-white p-5 shadow-sm">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h2 className="text-lg font-bold text-navy">
              Shift {day.shifts.length > 1 ? index + 1 : ""}
            </h2>
            <p className="text-sm text-muted">
              {item.loginTime} → {item.logoutTime}
            </p>
          </div>
          <div className="grid gap-3 sm:grid-cols-3">
            <Stat label="On shift" value={item.onShift} tone="ok" />
            <Stat label="Worked" value={item.worked} tone="purple" />
            <Stat label="Break time" value={item.breaksTotal} tone="orange" />
          </div>
          <BreakTable breaks={item.breaks} />
        </section>
      ))}
    </div>
  );
}
