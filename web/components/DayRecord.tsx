import Link from "next/link";
import { formatHrsMins, parseDurationSeconds } from "@/lib/format";
import { capLoginSeconds, GRACE_MINUTES, MAX_LOGIN_SECONDS, SHIFT_SECONDS } from "@/lib/shift";
import type { CalendarDay } from "@/lib/types";

export function DayRecord({ row, start, end }: { row: CalendarDay; start: string; end: string }) {
  if (row.kind === "off") {
    return (
      <article className="grid bg-[#E8F4FC] md:grid-cols-12">
        <div className="border-t border-line px-4 py-2.5 md:col-span-2">
          <p className="text-sm font-bold text-navy">{row.date}</p>
          <p className="text-xs capitalize text-muted">{row.weekday}</p>
        </div>
        <div className="border-t border-line px-4 py-2.5 text-sm text-muted md:col-span-3 md:border-l">
          Off day
        </div>
        <div className="border-t border-line px-4 py-2.5 md:col-span-5 md:border-l" />
        <div className="border-t border-line px-4 py-2.5 text-sm text-muted md:col-span-2 md:border-l">
          Off day
        </div>
      </article>
    );
  }

  if (row.kind === "absent" || !row.day) {
    return (
      <article className="grid bg-white md:grid-cols-12">
        <div className="border-t border-line bg-[#F7FAFF] px-4 py-2.5 md:col-span-2">
          <p className="text-sm font-bold text-navy">{row.date}</p>
          <p className="text-xs text-muted">{row.weekday}</p>
        </div>
        <div className="border-t border-line px-4 py-2.5 text-sm font-semibold text-danger md:col-span-3 md:border-l">
          Absent
        </div>
        <div className="border-t border-line px-4 py-2.5 md:col-span-5 md:border-l" />
        <div className="border-t border-line px-4 py-2.5 text-sm text-muted md:col-span-2 md:border-l">
          No shift
        </div>
      </article>
    );
  }

  const day = row.day;
  const shift = day.shifts[0];
  const productive = shift?.breaks.filter((b) => b.productive) ?? [];
  const other = shift?.breaks.filter((b) => !b.productive) ?? [];

  return (
    <article className="grid bg-white md:grid-cols-12">
      <div className="border-t border-line bg-[#1E5BB8] px-4 py-3 text-white md:col-span-2">
        <p className="text-sm font-bold">{day.date}</p>
        <p className="text-xs text-white/80">{day.weekday}</p>
        <Link
          href={`/days/${day.date}?start=${start}&end=${end}`}
          className="mt-2 inline-block text-xs font-semibold text-white/90 underline"
        >
          View details
        </Link>
      </div>

      <div className="border-t border-line px-4 py-3 text-sm md:col-span-3 md:border-l">
        <p className="mb-2 text-xs font-bold uppercase tracking-wide text-primary md:hidden">Timing info</p>
        <p>
          <span className="text-muted">Time in: </span>
          <span className="font-semibold">{shift?.loginTime || "--"}</span>
        </p>
        <p>
          <span className="text-muted">Time out: </span>
          <span className="font-semibold">{shift?.logoutTime || "--"}</span>
        </p>
        <p className="mt-1">
          Logged in duration:{" "}
          <span className="font-bold text-navy">
            {formatHrsMins(parseDurationSeconds(shift?.onShift))}
          </span>
        </p>
        <p>
          Calculated worked duration:{" "}
          <span className="font-bold text-purple">
            {formatHrsMins(parseDurationSeconds(shift?.worked))}
          </span>
        </p>
        {day.note ? <p className="mt-2 rounded-lg bg-soft px-2 py-1 text-xs text-navy">{day.note}</p> : null}
      </div>

      <div className="border-t border-line px-4 py-3 text-sm md:col-span-5 md:border-l">
        <p className="mb-2 text-xs font-bold uppercase tracking-wide text-primary md:hidden">Breaks info</p>
        <p>
          Total Break:{" "}
          <span className="font-bold">{formatHrsMins(parseDurationSeconds(shift?.breaksTotal))}</span>
        </p>
        <p>
          Non-productive:{" "}
          <span className="font-bold text-orange">
            {formatHrsMins(parseDurationSeconds(day.totals.nonProductiveBreaks))}
          </span>
          {" · "}
          Productive:{" "}
          <span className="font-bold text-ok">
            {formatHrsMins(parseDurationSeconds(day.totals.productiveBreaks))}
          </span>
        </p>
        <ul className="mt-2 space-y-1 text-xs">
          {[...productive, ...other].map((item, i) => (
            <li key={`${item.start}-${item.reason}-${i}`}>
              <span className="tabular-nums text-muted">
                {item.start} → {item.end}
              </span>{" "}
              ({item.duration}){" "}
              <span className={item.productive ? "font-semibold text-ok" : "font-semibold text-orange"}>
                {item.reason}
              </span>
            </li>
          ))}
          {!shift?.breaks.length ? <li className="text-muted">No breaks</li> : null}
        </ul>
      </div>

      <div className="border-t border-line px-4 py-3 text-sm md:col-span-2 md:border-l">
        <p className="mb-2 text-xs font-bold uppercase tracking-wide text-primary md:hidden">Shift info</p>
        <p>
          Shift start: <span className="font-semibold">{shift?.loginTime || "--"}</span>
        </p>
        <p>
          Shift end: <span className="font-semibold">{shift?.logoutTime || "--"}</span>
        </p>
        <p className="mt-1">
          Scheduled shift: <span className="font-bold">{formatHrsMins(SHIFT_SECONDS)}</span>
        </p>
        <p>
          Total shift (counted):{" "}
          <span className="font-bold text-ok">
            {formatHrsMins(capLoginSeconds(parseDurationSeconds(shift?.onShift)))}
          </span>
        </p>
        {parseDurationSeconds(shift?.onShift) > MAX_LOGIN_SECONDS ? (
          <p className="mt-1 text-xs font-semibold text-danger">
            Over cap (shift + {GRACE_MINUTES} mins) not counted:{" "}
            {formatHrsMins(parseDurationSeconds(shift?.onShift) - MAX_LOGIN_SECONDS)}
          </p>
        ) : null}
      </div>
    </article>
  );
}
