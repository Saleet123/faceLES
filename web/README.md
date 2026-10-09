# FaceLES web dashboard

Reads the same `attendance_logs/YYYY-MM-DD.json` files written by the desktop app and shows shifts **day by day**, with employee name, times, breaks, and shift notes.

## Run

From the repo root:

```bash
cd web
npm install
npm run dev
```

Open http://localhost:3000

The server looks for logs at `../attendance_logs` (the FaceLES folder). Override with:

```bash
FACELES_LOGS_DIR=/path/to/attendance_logs npm run dev
```

Employee name for older logs (before `employee_name` was written into JSON):

```bash
FACELES_EMPLOYEE_NAME="Saleet Ul Hassan" npm run dev
```

New FaceLES logouts also store `employee_name`, `employee_role`, and `username` on each session.
