export function FilterBar({
  start,
  end,
  employee,
  username,
}: {
  start: string;
  end: string;
  employee: string;
  username: string;
}) {
  const field =
    "h-9 w-full min-w-0 rounded-md border border-line px-2.5 text-xs text-navy";
  return (
    <form method="GET" action="/" className="min-w-0 overflow-hidden rounded-2xl border border-line bg-white p-3">
      <div className="flex min-w-0 flex-wrap items-end gap-2">
        <label className="min-w-[110px] flex-1">
          <span className="mb-1 block text-[11px] font-semibold text-muted">Search by ID</span>
          <input readOnly value={username || "saleet"} className={`${field} bg-soft`} />
        </label>
        <label className="min-w-[140px] flex-1">
          <span className="mb-1 block text-[11px] font-semibold text-muted">Search by Name</span>
          <input readOnly value={employee} className={`${field} bg-soft uppercase`} />
        </label>
        <label className="min-w-[128px] flex-1">
          <span className="mb-1 block text-[11px] font-semibold text-muted">Start Date</span>
          <input type="date" name="start" defaultValue={start} className={field} />
        </label>
        <label className="min-w-[128px] flex-1">
          <span className="mb-1 block text-[11px] font-semibold text-muted">End Date</span>
          <input type="date" name="end" defaultValue={end} className={field} />
        </label>
        <div className="flex shrink-0 items-center gap-1.5">
          <button
            type="submit"
            className="h-9 whitespace-nowrap rounded-md bg-primary px-3 text-xs font-bold text-white hover:bg-bright"
          >
            Get Attendance
          </button>
          <a
            href="/"
            className="inline-flex h-9 items-center whitespace-nowrap rounded-md border border-line bg-white px-3 text-xs font-semibold text-primary hover:bg-soft"
          >
            This month
          </a>
        </div>
      </div>
    </form>
  );
}
