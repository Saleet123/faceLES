import { NextRequest } from "next/server";
import { loadDaysInRange, resolveRange } from "@/lib/logs";

export const dynamic = "force-dynamic";

export function GET(request: NextRequest) {
  const { searchParams } = request.nextUrl;
  const range = resolveRange(searchParams.get("start") || undefined, searchParams.get("end") || undefined);
  const days = loadDaysInRange(range.start, range.end);
  const lines = [
    ["Date", "Weekday", "Employee", "Time in", "Time out", "Logged in", "Worked", "Breaks", "Note"].join(","),
  ];
  for (const day of days) {
    const shift = day.shifts[0];
    const cells = [
      day.date,
      day.weekday,
      csv(day.employeeName),
      csv(shift?.loginTime),
      csv(shift?.logoutTime),
      csv(shift?.onShift),
      csv(shift?.worked),
      csv(shift?.breaksTotal),
      csv(day.note),
    ];
    lines.push(cells.join(","));
  }
  const body = lines.join("\n");
  return new Response(body, {
    headers: {
      "Content-Type": "text/csv; charset=utf-8",
      "Content-Disposition": `attachment; filename="faceles-${range.start}-to-${range.end}.csv"`,
    },
  });
}

function csv(value: string | undefined): string {
  const text = value || "";
  if (/[",\n]/.test(text)) return `"${text.replaceAll('"', '""')}"`;
  return text;
}
