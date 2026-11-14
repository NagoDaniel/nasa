import { useEffect, useState } from 'react'
import { useI18n } from '../i18n'

export type Async<T> = { data: T | null; error: string | null; loading: boolean }

/** Fetch when `key` or the language changes (the backend writes texts in it); ignores stale responses. */
export function useAsync<T>(key: string | null, fn: () => Promise<T>): Async<T> {
  const { lang } = useI18n()
  const [state, setState] = useState<Async<T>>({ data: null, error: null, loading: !!key })
  useEffect(() => {
    if (!key) {
      setState({ data: null, error: null, loading: false })
      return
    }
    let live = true
    setState((s) => ({ ...s, loading: true, error: null }))
    fn().then(
      (data) => live && setState({ data, error: null, loading: false }),
      (e: unknown) => live && setState({ data: null, error: e instanceof Error ? e.message : String(e), loading: false }),
    )
    return () => {
      live = false
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key, lang])
  return state
}
