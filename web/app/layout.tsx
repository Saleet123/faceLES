import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "FaceLES · Attendance",
  description: "Day-wise shift dashboard from FaceLES attendance JSON logs.",
};

export const dynamic = "force-dynamic";

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen font-sans antialiased">
        <header className="bg-gradient-to-r from-deep via-primary to-bright text-white">
          <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
            <Link href="/" className="flex items-center gap-3">
              <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-white/15 text-lg font-extrabold">
                F
              </span>
              <span>
                <span className="block text-lg font-extrabold leading-tight">FaceLES</span>
                <span className="block text-xs text-white/80">Attendance dashboard</span>
              </span>
            </Link>
            <p className="hidden text-sm text-white/80 sm:block">Attendance · date range from attendance_logs</p>
          </div>
        </header>
        <main className="mx-auto max-w-7xl px-6 py-8">{children}</main>
      </body>
    </html>
  );
}
