import type { ReactNode } from 'react'
import { useI18n } from '../i18n'
import type { Dict } from '../i18n/en'
import { SECTIONS, type Role, type Section } from '../state/sections'

const P = { fill: 'none', stroke: 'currentColor', strokeWidth: 1.7, strokeLinecap: 'round', strokeLinejoin: 'round' } as const
const ICONS: Record<Section, ReactNode> = {
  overview: <><rect x="3" y="3" width="6" height="6" rx="1" {...P} /><rect x="11" y="3" width="6" height="6" rx="1" {...P} /><rect x="3" y="11" width="6" height="6" rx="1" {...P} /><rect x="11" y="11" width="6" height="6" rx="1" {...P} /></>,
  weather: <><path d="M6 12a3.5 3.5 0 0 1 .6-6.9A4.5 4.5 0 0 1 15 6.5 3 3 0 0 1 14.5 12z" {...P} /><path d="M7 15l-.8 2M10.5 15l-.8 2M14 15l-.8 2" {...P} /></>,
  risks: <><path d="M10 3l7.5 13h-15z" {...P} /><path d="M10 8v4M10 14.2v.3" {...P} /></>,
  field: <><path d="M4 5l5-2 7 3-1 10-6 1-5-4z" {...P} /><path d="M4 5l5 4 7-3M9 9v8" {...P} /></>,
  soil: <><path d="M10 3l7 3.5-7 3.5-7-3.5z" {...P} /><path d="M3 10l7 3.5 7-3.5M3 13.5L10 17l7-3.5" {...P} /></>,
  crops: <><path d="M10 17V9" {...P} /><path d="M10 11C10 7 7 5.5 3.5 5.5 3.5 9 6 11 10 11zM10 9c0-3 2.2-5 6.5-5C16.5 7 14 9 10 9z" {...P} /></>,
  plan: <><rect x="3.5" y="4" width="13" height="12.5" rx="1.5" {...P} /><path d="M3.5 8h13M7 2.5v3M13 2.5v3M7 11.5l2 2 4-4" {...P} /></>,
  rotations: <><path d="M16 10a6 6 0 0 1-10.5 4M4 10a6 6 0 0 1 10.5-4" {...P} /><path d="M14.5 3v3h-3M5.5 17v-3h3" {...P} /></>,
  sourcing: <><path d="M10 17.500s5.5-5 5.5-9.200a5.5 5.5 0 0 0-11 0c0 4.2 5.5 9.2 5.5 9.200z" {...P} /><circle cx="10" cy="8.3" r="2" {...P} /></>,
  recs: <><path d="M7.5 14.500h5M8.3 17h3.400M6.3 11.800a5 5 0 1 1 7.4 0c-.7.8-1.2 1.5-1.2 2.700h-5c0-1.2-.5-1.9-1.2-2.700z" {...P} /></>,
  trends: <><path d="M3 17h14" {...P} /><path d="M5.5 14v-4M10 14V5.500M14.5 14V8.5" {...P} /></>,
}

export default function Sidebar({ role, setRole, section, setSection, collapsed, setCollapsed }: {
  role: Role
  setRole: (r: Role) => void
  section: Section
  setSection: (s: Section) => void
  collapsed: boolean
  setCollapsed: (c: boolean) => void
}) {
  const { t, lang, setLang } = useI18n()
  return (
    <nav className="sidebar" aria-label="Sections">
      <div className="side-top">
        <div className="brand">
          <span className="brand-mark">S2F</span>
          <span className="brand-text"><strong>SPACE2FEED</strong><span>{t('appTagline')}</span></span>
        </div>
        <button type="button" className="side-collapse" onClick={() => setCollapsed(!collapsed)} title={collapsed ? t('openMenu') : t('collapseMenu')} aria-label={collapsed ? t('openMenu') : t('collapseMenu')}>
          <svg viewBox="0 0 16 16" width="14" height="14" aria-hidden="true"><path d={collapsed ? 'M6 3l5 5-5 5' : 'M10 3L5 8l5 5'} fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" /></svg>
        </button>
      </div>

      <div className="role-switch" role="tablist">
        {(['farmer', 'procurement'] as Role[]).map((r) => (
          <button key={r} type="button" role="tab" aria-selected={role === r} className={role === r ? 'on' : ''} onClick={() => setRole(r)} title={t(r === 'farmer' ? 'tabFarmer' : 'tabProcurement')}>
            <span className="role-long">{t(r === 'farmer' ? 'tabFarmer' : 'tabProcurement')}</span>
            <span className="role-short">{t(r === 'farmer' ? 'tabFarmer' : 'tabProcurement').slice(0, 1)}</span>
          </button>
        ))}
      </div>

      <ul className="side-nav">
        {SECTIONS[role].map((s) => (
          <li key={s}>
            <button type="button" className={section === s ? 'on' : ''} aria-current={section === s ? 'page' : undefined} onClick={() => setSection(s)} title={t(`nav_${s}` as keyof Dict)}>
              <svg viewBox="0 0 20 20" width="18" height="18" aria-hidden="true">{ICONS[s]}</svg>
              <span className="nav-label">{t(`nav_${s}` as keyof Dict)}</span>
            </button>
          </li>
        ))}
      </ul>

      <div className="side-bottom">
        <div className="seg lang">
          <button type="button" className={lang === 'en' ? 'on' : ''} onClick={() => setLang('en')}>EN</button>
          <button type="button" className={lang === 'ro' ? 'on' : ''} onClick={() => setLang('ro')}>RO</button>
        </div>
        <p className="side-note">{t('notEndorsed')}</p>
      </div>
    </nav>
  )
}
