import { useEffect, useState } from 'react'

/** Текущее время, которое обновляется раз в интервал. Рендер остаётся чистым: время — это состояние */
export function useNow(intervalMs = 60_000): number {
  const [now, setNow] = useState(() => Date.now())
  useEffect(() => {
    const t = setInterval(() => setNow(Date.now()), intervalMs)
    return () => clearInterval(t)
  }, [intervalMs])
  return now
}
