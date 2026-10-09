export function Stat({
  label,
  value,
  tone = "navy",
}: {
  label: string;
  value: string;
  tone?: "navy" | "ok" | "orange" | "purple" | "primary";
}) {
  const colors = {
    navy: "text-navy",
    ok: "text-ok",
    orange: "text-orange",
    purple: "text-purple",
    primary: "text-primary",
  };
  return (
    <div className="rounded-2xl border border-line bg-white p-4">
      <p className="text-xs font-semibold uppercase tracking-wide text-muted">{label}</p>
      <p className={`mt-1 text-2xl font-extrabold tabular-nums ${colors[tone]}`}>{value}</p>
    </div>
  );
}
