import path from "path";
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  outputFileTracingRoot: path.resolve(__dirname),
  env: {
    FACELES_LOGS_DIR: process.env.FACELES_LOGS_DIR || path.resolve(process.cwd(), "..", "attendance_logs"),
    FACELES_EMPLOYEE_NAME: process.env.FACELES_EMPLOYEE_NAME || "Saleet Ul Hassan",
    FACELES_EMPLOYEE_ROLE: process.env.FACELES_EMPLOYEE_ROLE || "Employee · Face-verified attendance",
  },
};

export default nextConfig;
