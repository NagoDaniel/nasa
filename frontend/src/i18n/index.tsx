import { createContext, useContext, useMemo, useState, type ReactNode } from 'react'
import { en, type Dict } from './en'
import { ro } from './ro'
import { setApiLang } from '../api/client'
import { setNumberLocale } from '../components/format'

export type Lang = 'en' | 'ro'
const DICTS: Record<Lang, Dict> = { en, ro }

type Ctx = { lang: Lang; setLang: (l: Lang) => void; t: (k: keyof Dict) => string }
const I18n = createContext<Ctx | null>(null)

function initialLang(): Lang {
  let l: Lang = 'en'
  try {
    const v = localStorage.getItem('s2f.lang')
    if (v === 'en' || v === 'ro') l = v
  } catch {
    /* storage unavailable */
  }
  setApiLang(l)
  setNumberLocale(l)
  return l
}

export function I18nProvider({ children }: { children: ReactNode }) {
  const [lang, setLangState] = useState<Lang>(initialLang)
  const value = useMemo<Ctx>(() => {
    const setLang = (l: Lang) => {
      setApiLang(l) // before the re-render, so refetches already ask for the new language
      setNumberLocale(l)
      setLangState(l)
      try {
        localStorage.setItem('s2f.lang', l)
      } catch {
        /* ignore */
      }
      document.documentElement.lang = l
    }
    return { lang, setLang, t: (k) => DICTS[lang][k] ?? en[k] }
  }, [lang])
  return <I18n.Provider value={value}>{children}</I18n.Provider>
}

export function useI18n(): Ctx {
  const c = useContext(I18n)
  if (!c) throw new Error('useI18n outside I18nProvider')
  return c
}
