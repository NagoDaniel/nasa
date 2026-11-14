import { useState } from 'react'
import RomaniaMap, { type AreaSelection } from './map/RomaniaMap'
import { REGION_COLORS } from './map/regionColors'

export default function App() {
  const [sel, setSel] = useState<AreaSelection | null>(null)

  return (
    <div className="app">
      <header className="topbar">
        <strong>SPACE2FEED</strong>
        <span className="muted">Field Shift · Smart Feed</span>
      </header>
      <main className="body">
        <RomaniaMap onSelect={setSel} />
        <aside className="panel">
          <h2>Selected area</h2>
          {!sel && <p className="muted">Click a county, or zoom in and click a commune.</p>}
          {sel?.kind === 'county' && (
            <dl>
              <dt>County (județ)</dt><dd>{sel.name} <span className="muted">({sel.code})</span></dd>
              <dt>Development region</dt><dd>{sel.region} <span className="muted">({sel.nuts2})</span></dd>
            </dl>
          )}
          {sel?.kind === 'commune' && (
            <dl>
              <dt>Commune / town (UAT)</dt><dd>{sel.name}</dd>
              <dt>County (județ)</dt><dd>{sel.countyName} <span className="muted">({sel.county})</span></dd>
              <dt>Development region</dt><dd>{sel.region}</dd>
            </dl>
          )}
          <h3>Development regions</h3>
          <ul className="legend">
            {Object.entries(REGION_COLORS).map(([name, color]) => (
              <li key={name}><i style={{ background: color }} />{name}</li>
            ))}
          </ul>
          <p className="muted small">Commune borders are shown for Alba and its neighbours (zoom in).</p>
        </aside>
      </main>
    </div>
  )
}
