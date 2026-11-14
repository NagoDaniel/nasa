import { createContext, useContext, useMemo, useState, type ReactNode } from 'react'
import { en, type Dict } from './en'
import { ro } from './ro'

export type Lang = 'en' | 'ro'
const DICTS: Record<Lang, Dict> = { en, ro }

type Ctx = { lang: Lang; setLang: (l: Lang) => void; t: (k: keyof Dict) => string }
const I18n = createContext<Ctx | null>(null)

function initialLang(): Lang {
  try {
    const v = localStorage.getItem('s2f.lang')
    if (v === 'en' || v === 'ro') return v
  } catch {
    /* storage unavailable */
  }
  return 'en'
}

export function I18nProvider({ children }: { children: ReactNode }) {
  const [lang, setLangState] = useState<Lang>(initialLang)
  const value = useMemo<Ctx>(() => {
    const setLang = (l: Lang) => {
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
