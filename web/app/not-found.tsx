import Link from "next/link";

export default function NotFound() {
  return (
    <div className="rounded-3xl border border-line bg-white p-10 text-center">
      <h1 className="text-xl font-extrabold text-navy">Day not found</h1>
      <p className="mt-2 text-sm text-muted">That date has no attendance JSON yet.</p>
      <Link href="/" className="mt-4 inline-block text-sm font-semibold text-primary hover:underline">
        Back to all days
      </Link>
    </div>
  );
}
