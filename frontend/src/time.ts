// Flight times are entered and shown in Pacific time, because every
// airport we serve (SJC, SFO, OAK) is in California, wherever the
// student's laptop thinks it is.

export const PACIFIC = 'America/Los_Angeles'

/** Pacific's offset from UTC, in minutes, at a given instant (e.g. -480 in winter). */
function pacificOffsetMinutes(at: Date): number {
  const name = new Intl.DateTimeFormat('en-US', { timeZone: PACIFIC, timeZoneName: 'longOffset' })
    .formatToParts(at)
    .find((p) => p.type === 'timeZoneName')!.value // like "GMT-08:00"
  const match = /GMT([+-])(\d{2}):(\d{2})/.exec(name)
  if (!match) return 0
  const minutes = Number(match[2]) * 60 + Number(match[3])
  return match[1] === '-' ? -minutes : minutes
}

/**
 * "2026-12-12T11:00" typed into a date-time box, read as Pacific time,
 * becomes the exact instant "2026-12-12T19:00:00.000Z".
 */
export function pacificInputToISO(local: string): string {
  const [date, time] = local.split('T')
  const [y, mo, d] = date.split('-').map(Number)
  const [h, mi] = time.split(':').map(Number)
  const asIfUTC = Date.UTC(y, mo - 1, d, h, mi)
  // Guess the offset, then re-check it at the corrected instant, which
  // matters for times near the daylight-saving switch.
  let instant = asIfUTC - pacificOffsetMinutes(new Date(asIfUTC)) * 60_000
  instant = asIfUTC - pacificOffsetMinutes(new Date(instant)) * 60_000
  return new Date(instant).toISOString()
}

/** "Sat, Dec 12, 8:10 AM" in Pacific time. */
export function formatPacific(iso: string): string {
  return new Date(iso).toLocaleString('en-US', {
    timeZone: PACIFIC,
    weekday: 'short',
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  })
}
