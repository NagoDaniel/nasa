import { useState } from 'react'
import { I18nProvider, useI18n } from './i18n'
import { useExplain } from './i18n/explain'
import RomaniaMap, { type AreaSelection, type Choropleth } from './map/RomaniaMap'
import { AOI } from './map/style'
import FarmerView from './views/farmer/FarmerView'
import ProcurementView from './views/procurement/ProcurementView'

const AOI_BOUNDS: [[number, number], [number, number]] = [[20.6, 44.4], [25.4, 47.7]]
type Tab = 'farmer' | 'procurement'

const ALBA: AreaSelection = { kind: 'county', code: 'AB', name: 'Alba', region: 'Centru', nuts2: 'RO12' }

function Shell() {
  const { t, lang, setLang } = useI18n()
  const x = useExplain()
  const [tab, setTab] = useState<Tab>('farmer')
  const [sel, setSel] = useState<AreaSelection>(ALBA)
  const [choropleth, setChoropleth] = useState<Choropleth>(null)

  const countyCode = sel.kind === 'county' ? sel.code : sel.county
  const inAoi = AOI.includes(countyCode)
  const unitId = sel.kind === 'county' ? sel.code : sel.id
  const countyName = sel.kind === 'county' ? sel.name : sel.countyName

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <strong>SPACE2FEED</strong>
          <span className="muted">{t('appTagline')}</span>
        </div>
        <nav className="tabs">
          <button className={tab === 'farmer' ? 'on' : ''} onClick={() => setTab('farmer')}>{t('tabFarmer')}</button>
          <button className={tab === 'procurement' ? 'on' : ''} onClick={() => setTab('procurement')}>{t('tabProcurement')}</button>
        </nav>
        <div className="seg lang">
          <button className={lang === 'en' ? 'on' : ''} onClick={() => setLang('en')}>EN</button>
          <button className={lang === 'ro' ? 'on' : ''} onClick={() => setLang('ro')}>RO</button>
        </div>
      </header>
      <main className="body">
        <aside className="map-pane">
          <RomaniaMap
            onSelect={(s) => s && setSel(s)}
            initialBounds={AOI_BOUNDS}
            choropleth={tab === 'procurement' ? choropleth : null}
            legendLow={t('legendLow')}
            legendHigh={t('legendHigh')}
            legendInfo={x.procurement.choropleth}
          />
          <div className="selection">
            <div className="muted tiny">{sel.kind === 'county' ? t('county') : t('commune')}</div>
            <div className="sel-name">
              {sel.name}
              {sel.kind === 'commune' && <span className="muted"> · {sel.countyName}</span>}
              <span className="muted"> · {sel.region}</span>
            </div>
            {!inAoi && <div className="note warn small">{sel.name} {t('outsideAoi')}</div>}
            {inAoi && <div className="muted tiny">{t('selectHint')}</div>}
          </div>
        </aside>
        <section className="dash">
          {tab === 'farmer' && (inAoi
            ? <FarmerView key={unitId} unitId={unitId} countyName={countyName} />
            : <p className="note warn">{sel.name} {t('outsideAoi')}</p>)}
          {tab === 'procurement' && <ProcurementView onChoropleth={setChoropleth} selectedCounty={inAoi ? countyCode : null} />}
          <footer className="foot muted tiny">
            Built at the NASA Space Apps Challenge 2026 (Alba Iulia). Not endorsed by NASA. Data: NASA POWER, GPM IMERG, GLDAS, FIRMS · ISRIC SoilGrids · INS TEMPO · geoBoundaries · © OpenStreetMap contributors.
          </footer>
        </section>
      </main>
    </div>
  )
}

export default function App() {
  return (
    <I18nProvider>
      <Shell />
    </I18nProvider>
  )
}
