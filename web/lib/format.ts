export function cleanDuration(raw: string | undefined): string {
  if (!raw) return "00:00:00";
  const text = String(raw).split(".")[0];
  const parts = text.split(":");
  if (parts.length === 3) {
    const [h, m, s] = parts.map((p) => String(Number(p) || 0).padStart(2, "0"));
    return `${h}:${m}:${s}`;
  }
  return text || "00:00:00";
}

export function parseDurationSeconds(raw: string | undefined): number {
  const cleaned = cleanDuration(raw);
  const [h, m, s] = cleaned.split(":").map((n) => Number(n) || 0);
  return h * 3600 + m * 60 + s;
}

export function formatSeconds(total: number): string {
  const safe = Math.max(0, Math.round(total));
  const h = Math.floor(safe / 3600);
  const m = Math.floor((safe % 3600) / 60);
  const s = safe % 60;
  return [h, m, s].map((n) => String(n).padStart(2, "0")).join(":");
}

export function formatDayLabel(iso: string): { label: string; weekday: string } {
  const date = new Date(`${iso}T12:00:00`);
  if (Number.isNaN(date.getTime())) return { label: iso, weekday: "" };
  return {
    label: date.toLocaleDateString(undefined, {
      day: "numeric",
      month: "long",
      year: "numeric",
    }),
    weekday: date.toLocaleDateString(undefined, { weekday: "long" }),
  };
}

export function initials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (!parts.length) return "FL";
  return parts.slice(0, 2).map((p) => p[0]?.toUpperCase() ?? "").join("");
}

export function formatHrsMins(seconds: number): string {
  const safe = Math.max(0, Math.round(seconds));
  const h = Math.floor(safe / 3600);
  const m = Math.floor((safe % 3600) / 60);
  return `${String(h).padStart(2, "0")} Hrs : ${String(m).padStart(2, "0")} Mins`;
}

export function isoDate(date: Date): string {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, "0");
  const d = String(date.getDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
}

export function todayIso(): string {
  return new Date().toLocaleDateString("en-CA", {
    timeZone: process.env.FACELES_TZ || "Asia/Karachi",
  });
}

export function clampRangeEnd(start: string, end: string, cap: string = todayIso()): string {
  const until = end <= cap ? end : cap;
  return until < start ? start : until;
}

export function monthBounds(from: Date = new Date()): { start: string; end: string; label: string } {
  const start = new Date(from.getFullYear(), from.getMonth(), 1);
  const end = new Date(from.getFullYear(), from.getMonth() + 1, 0);
  return {
    start: isoDate(start),
    end: isoDate(end),
    label: start.toLocaleDateString(undefined, { month: "long", year: "numeric" }),
  };
}

export function isProductiveBreak(reason: string): boolean {
  const key = reason.trim().toLowerCase();
  return ["meeting", "lunch", "prayer", "tea", "call"].includes(key);
}

export function isWeekday(iso: string): boolean {
  const day = new Date(`${iso}T12:00:00`).getDay();
  return day !== 0 && day !== 6;
}

export function eachIsoDate(start: string, end: string): string[] {
  const out: string[] = [];
  const cursor = new Date(`${start}T12:00:00`);
  const last = new Date(`${end}T12:00:00`);
  if (Number.isNaN(cursor.getTime()) || Number.isNaN(last.getTime())) return out;
  while (cursor <= last) {
    out.push(isoDate(cursor));
    cursor.setDate(cursor.getDate() + 1);
  }
  return out;
}
