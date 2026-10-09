/** Scheduled shift length and daily login cap (shift + 30 minutes grace). */
export const SHIFT_HOURS = Number(process.env.FACELES_SHIFT_HOURS || 8);
export const GRACE_MINUTES = Number(process.env.FACELES_SHIFT_GRACE_MINUTES || 30);
export const SHIFT_SECONDS = Math.max(1, SHIFT_HOURS) * 3600;
export const GRACE_SECONDS = Math.max(0, GRACE_MINUTES) * 60;
export const MAX_LOGIN_SECONDS = SHIFT_SECONDS + GRACE_SECONDS;

export function capLoginSeconds(seconds: number): number {
  return Math.min(Math.max(0, seconds), MAX_LOGIN_SECONDS);
}
