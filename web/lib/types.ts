export type BreakRow = [string, string, string, string];

export type RawSession = {
  login_time?: string;
  logout_time?: string;
  login_duration?: string;
  work_duration?: string;
  total_break_time?: string;
  breaks?: Array<string[]>;
  shift_note?: string;
  employee_name?: string;
  employee_role?: string;
  username?: string;
  ip_address?: string;
  hostname?: string;
  user?: string;
  platform?: string;
};

export type RawDayLog = {
  date?: string;
  shift_note?: string;
  sessions?: RawSession[];
};

export type Shift = {
  loginTime: string;
  logoutTime: string;
  onShift: string;
  worked: string;
  breaksTotal: string;
  note: string;
  employeeName: string;
  employeeRole: string;
  username: string;
  hostname: string;
  ip: string;
  platform: string;
  breaks: {
    start: string;
    end: string;
    duration: string;
    reason: string;
    productive: boolean;
  }[];
};

export type DayShift = {
  date: string;
  label: string;
  weekday: string;
  note: string;
  employeeName: string;
  employeeRole: string;
  shifts: Shift[];
  totals: {
    worked: string;
    breaks: string;
    onShift: string;
    breakCount: number;
    productiveBreaks: string;
    nonProductiveBreaks: string;
  };
};

export type RangeSummary = {
  start: string;
  end: string;
  through: string;
  monthLabel: string;
  daysLogged: number;
  weekdays: number;
  weekdaysAbsent: number;
  offDays: number;
  employeeName: string;
  employeeRole: string;
  username: string;
  logged: string;
  loggedRaw: string;
  overtime: string;
  shift: string;
  shiftHours: number;
  graceMinutes: number;
  worked: string;
  breaks: string;
  productiveBreaks: string;
  nonProductiveBreaks: string;
  notes: number;
};

export type CalendarDay = {
  date: string;
  weekday: string;
  kind: "worked" | "off" | "absent";
  day?: DayShift;
};
