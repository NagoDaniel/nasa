import { useCallback, useEffect, useRef, useState } from 'react'
import { postChat } from '../api/client'
import type { AssistantAction, AssistantChoice, ChatContext, ChatResponse, ChatTurn } from '../api/types'

export type Msg = {
  id: number
  role: 'user' | 'assistant'
  text: string
  sig?: string
  mode?: ChatResponse['mode'] | 'error'
  choices?: AssistantChoice[]
  sources?: string[]
  unverified?: string[]
  applied?: number
}

const HISTORY_TURNS = 6

/** Chat state. Messages live in memory only (nothing is stored in the browser). */
export function useAssistant(onActions: (a: AssistantAction[]) => number, netError: string) {
  const [messages, setMessages] = useState<Msg[]>([])
  const [busy, setBusy] = useState(false)
  const [cooldownUntil, setCooldownUntil] = useState(0)
  const [now, setNow] = useState(() => Date.now())
  const nextId = useRef(1)
  const ctrl = useRef<AbortController | null>(null)
  const actionsRef = useRef(onActions)
  useEffect(() => {
    actionsRef.current = onActions
  }, [onActions])

  useEffect(() => () => ctrl.current?.abort(), [])
  useEffect(() => {
    if (cooldownUntil <= Date.now()) return
    const t = window.setInterval(() => {
      const n = Date.now()
      setNow(n)
      if (n >= cooldownUntil) window.clearInterval(t)
    }, 500)
    return () => window.clearInterval(t)
  }, [cooldownUntil])
  const cooldown = Math.max(0, Math.ceil((cooldownUntil - now) / 1000))

  const send = useCallback(async (text: string, context: ChatContext) => {
    const message = text.trim()
    if (!message || busy || cooldownUntil > Date.now()) return
    // Only turns the server produced (signed) or the user typed go back as history.
    const history: ChatTurn[] = messages
      .filter((m) => m.role === 'user' || (m.sig && m.mode !== 'error'))
      .slice(-HISTORY_TURNS)
      .map((m) => (m.role === 'user' ? { role: 'user', text: m.text } : { role: 'assistant', text: m.text, sig: m.sig }))
    setMessages((ms) => [...ms, { id: nextId.current++, role: 'user', text: message }])
    setBusy(true)
    ctrl.current?.abort()
    const c = new AbortController()
    ctrl.current = c
    try {
      const r = await postChat(message, history, context, c.signal)
      const applied = r.actions.length ? actionsRef.current(r.actions) : 0
      if (r.retryAfter) {
        setCooldownUntil(Date.now() + r.retryAfter * 1000)
        setNow(Date.now())
      }
      setMessages((ms) => [...ms, {
        id: nextId.current++, role: 'assistant', text: r.reply, sig: r.sig, mode: r.mode,
        choices: r.choices, sources: r.sources, unverified: r.unverified, applied,
      }])
    } catch (e) {
      if ((e as Error).name === 'AbortError') return
      setMessages((ms) => [...ms, { id: nextId.current++, role: 'assistant', text: netError, mode: 'error' }])
    } finally {
      if (ctrl.current === c) {
        ctrl.current = null
        setBusy(false)
      }
    }
  }, [busy, cooldownUntil, messages, netError])

  const clear = useCallback(() => {
    ctrl.current?.abort()
    ctrl.current = null
    setBusy(false)
    setMessages([])
  }, [])

  return { messages, busy, cooldown, send, clear }
}
