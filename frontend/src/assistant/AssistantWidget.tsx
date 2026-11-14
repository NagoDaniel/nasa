import { Fragment, useCallback, useEffect, useRef, useState, type ReactNode } from 'react'
import { getAssistantStatus } from '../api/client'
import type { AssistantAction, Unit } from '../api/types'
import Info from '../components/Info'
import { useAsync } from '../components/useAsync'
import { useI18n } from '../i18n'
import { useMapLink } from '../state/MapLink'
import type { Role } from '../state/sections'
import { applyActions } from './actions'
import { ASSISTANT_TEXT } from './text'
import { useAssistant, type Msg } from './useAssistant'

const MAX_CHARS = 500

/** Plain text with "- " bullet lines; never rendered as HTML. */
function Rich({ text }: { text: string }) {
  const out: ReactNode[] = []
  let list: string[] = []
  const flush = (k: number) => {
    if (list.length) out.push(<ul key={`u${k}`}>{list.map((l, i) => <li key={i}>{l}</li>)}</ul>)
    list = []
  }
  text.split('\n').forEach((line, i) => {
    const m = /^\s*[-•]\s+(.*)$/.exec(line)
    if (m) return list.push(m[1])
    flush(i)
    if (line.trim()) out.push(<p key={i}>{line}</p>)
  })
  flush(-1)
  return <>{out}</>
}

/** Floating chat over the map: answers from the dashboard data and drives the map. */
export default function AssistantWidget({ byId, selectedId, role, section }: {
  byId: Map<string, Unit>
  selectedId: string
  role: Role
  section: string
}) {
  const { lang } = useI18n()
  const T = ASSISTANT_TEXT[lang]
  const { selectArea, goTo, runCommand } = useMapLink()
  const [open, setOpen] = useState(false)
  const [draft, setDraft] = useState('')
  const status = useAsync(open ? 'assistant-status' : null, getAssistantStatus)
  const max = status.data?.max_chars ?? MAX_CHARS

  const onActions = useCallback((a: AssistantAction[]) => applyActions(a, { byId, selectArea, goTo, runCommand }), [byId, selectArea, goTo, runCommand])
  const { messages, busy, cooldown, send, clear } = useAssistant(onActions, T.netError)

  const listRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)
  useEffect(() => {
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages, busy])
  useEffect(() => {
    if (open) inputRef.current?.focus()
  }, [open])
  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && setOpen(false)
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open])

  const submit = (text: string) => {
    if (!text.trim() || busy || cooldown) return
    void send(text.slice(0, max), { unit_id: selectedId || null, role, section, lang })
    setDraft('')
  }

  if (!open) {
    return (
      <button type="button" className="asst-fab" onClick={() => setOpen(true)} aria-label={T.open} title={T.open}>
        <svg viewBox="0 0 24 24" width="22" height="22" aria-hidden="true">
          <path d="M4 5.5A2.5 2.5 0 0 1 6.5 3h11A2.5 2.5 0 0 1 20 5.5v8a2.5 2.5 0 0 1-2.5 2.5H10l-4.2 3.6c-.5.4-1.3.1-1.3-.6V16A2.5 2.5 0 0 1 4 13.5z" fill="currentColor" />
          <path d="M9 9.5h.01M12 9.5h.01M15 9.5h.01" stroke="var(--accent)" strokeWidth="2.4" strokeLinecap="round" />
        </svg>
        <span className="asst-fab-label">{T.title}</span>
      </button>
    )
  }

  const suggestions = role === 'farmer' ? T.suggestFarmer : T.suggestProcurement
  const sendBlocked = busy || cooldown > 0

  return (
    <div className="asst" role="dialog" aria-label={T.title}>
      <header className="asst-head">
        <div className="asst-title">
          <strong>{T.title}</strong>
          <span className="asst-badge">{T.badge}</span>
          <Info wide>{T.role.split('\n\n').map((p, i) => <p key={i} style={{ marginTop: i ? 8 : 0 }}>{p}</p>)}</Info>
        </div>
        <div className="asst-head-btns">
          {messages.length > 0 && <button type="button" className="link small" onClick={clear}>{T.clear}</button>}
          <button type="button" className="asst-close" onClick={() => setOpen(false)} aria-label={T.close} title={T.close}>
            <svg viewBox="0 0 16 16" width="13" height="13" aria-hidden="true"><path d="M3 3l10 10M13 3L3 13" stroke="currentColor" strokeWidth="2" strokeLinecap="round" /></svg>
          </button>
        </div>
      </header>

      <div className="asst-list" ref={listRef} aria-live="polite">
        {messages.length === 0 && (
          <div className="asst-intro">
            <p>{T.intro}</p>
            {status.data && !status.data.llm && <p className="note warn small">{T.offlineNote}</p>}
            <div className="asst-suggest">
              {suggestions.map((s) => (
                <button key={s} type="button" className="chip" disabled={sendBlocked} onClick={() => submit(s)}>{s}</button>
              ))}
            </div>
          </div>
        )}
        {messages.map((m) => <Bubble key={m.id} m={m} byId={byId} onPick={selectArea} />)}
        {busy && <div className="asst-msg bot asst-typing"><span /><span /><span /> <em>{T.thinking}</em></div>}
      </div>

      <form className="asst-input" onSubmit={(e) => { e.preventDefault(); submit(draft) }}>
        <textarea
          ref={inputRef}
          rows={2}
          value={draft}
          maxLength={max}
          placeholder={T.placeholder}
          aria-label={T.placeholder}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) {
              e.preventDefault()
              submit(draft)
            }
          }}
        />
        <div className="asst-input-row">
          <span className={`tiny ${draft.length > max * 0.9 ? 'asst-count-warn' : 'muted'}`}>{draft.length}/{max}</span>
          {cooldown > 0 && <span className="tiny asst-count-warn">{T.wait.replace('{n}', String(cooldown))}</span>}
          <button type="submit" className="asst-send" disabled={sendBlocked || !draft.trim()}>{T.send}</button>
        </div>
      </form>
    </div>
  )
}

function Bubble({ m, byId, onPick }: { m: Msg; byId: Map<string, Unit>; onPick: (id: string) => void }) {
  const { lang } = useI18n()
  const T = ASSISTANT_TEXT[lang]
  if (m.role === 'user') return <div className="asst-msg me">{m.text}</div>
  const cls = m.mode === 'refused' || m.mode === 'limited' || m.mode === 'error' ? 'warn' : ''
  return (
    <div className={`asst-msg bot ${cls}`}>
      <Rich text={m.text} />
      {!!m.choices?.length && (
        <div className="asst-choices">
          {m.choices.filter((c) => byId.has(c.id)).map((c) => (
            <button key={c.id} type="button" className="chip" onClick={() => onPick(c.id)}>
              {c.name} <span className="muted">· {c.county_name}</span>
            </button>
          ))}
        </div>
      )}
      <div className="asst-meta">
        {m.mode === 'llm' && <span className="asst-tag ai">{T.aiTag}</span>}
        {(m.mode === 'rule' || m.mode === 'offline') && <span className="asst-tag">{T.ruleTag}</span>}
        {!!m.applied && <span className="asst-tag ok">✓ {T.did}</span>}
        {!!m.unverified?.length && <span className="asst-tag warn">⚠ {T.unverified}: {m.unverified.join(', ')}</span>}
        {!!m.sources?.length && (
          <details className="asst-sources">
            <summary>{T.sources}</summary>
            {m.sources.map((s, i) => <Fragment key={i}><span>{s}</span><br /></Fragment>)}
          </details>
        )}
      </div>
    </div>
  )
}
