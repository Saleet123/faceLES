import type { Shift } from "@/lib/types";

const REASON_TONE: Record<string, string> = {
  Logout: "bg-soft text-primary",
  "Idle Sitting": "bg-[#FFF6ED] text-orange",
  "Inactivity Only": "bg-[#FFF6ED] text-orange",
  "Absence Only": "bg-[#FFF0F1] text-danger",
  "Inactivity + Absence": "bg-[#FFF0F1] text-danger",
  Tea: "bg-[#F3F0FF] text-purple",
  Lunch: "bg-[#F3F0FF] text-purple",
  Prayer: "bg-soft text-deep",
  Call: "bg-soft text-deep",
  Meeting: "bg-soft text-deep",
};

export function BreakTable({ breaks }: { breaks: Shift["breaks"] }) {
  if (!breaks.length) {
    return <p className="text-sm text-muted">No breaks recorded for this shift.</p>;
  }
  return (
    <div className="overflow-hidden rounded-2xl border border-line">
      <table className="w-full text-left text-sm">
        <thead className="bg-soft text-xs font-bold uppercase tracking-wide text-muted">
          <tr>
            <th className="px-4 py-3">Start</th>
            <th className="px-4 py-3">End</th>
            <th className="px-4 py-3">Duration</th>
            <th className="px-4 py-3">Reason</th>
            <th className="px-4 py-3">Type</th>
          </tr>
        </thead>
        <tbody>
          {breaks.map((row, i) => (
            <tr key={`${row.start}-${row.reason}-${i}`} className="border-t border-line bg-white">
              <td className="px-4 py-3 tabular-nums">{row.start}</td>
              <td className="px-4 py-3 tabular-nums">{row.end}</td>
              <td className="px-4 py-3 font-semibold tabular-nums">{row.duration}</td>
              <td className="px-4 py-3">
                <span
                  className={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ${
                    REASON_TONE[row.reason] || "bg-soft text-navy"
                  }`}
                >
                  {row.reason}
                </span>
              </td>
              <td className="px-4 py-3 text-xs font-semibold">
                {row.productive ? <span className="text-ok">Productive</span> : <span className="text-orange">Non-productive</span>}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
