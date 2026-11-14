import type { Priorities } from '../../api/types'
import Card from '../../components/Card'
import Info from '../../components/Info'
import { useI18n } from '../../i18n'
import { useExplain } from '../../i18n/explain'

const KEYS: (keyof Priorities)[] = ['yield', 'water', 'soil', 'risk']

export default function PrioritiesPanel({ value, onChange }: { value: Priorities; onChange: (p: Priorities) => void }) {
  const { t } = useI18n()
  const x = useExplain()
  const sum = KEYS.reduce((a, k) => a + value[k], 0) || 1
  return (
    <Card title={t('priorities')} sub={t('prioritiesSub')} info={x.priorities}>
      <div className="sliders">
        {KEYS.map((k) => (
          <label key={k} className="slider">
            <span>{t(`p_${k}` as const)}</span>
            <input type="range" min={0} max={100} step={5} value={value[k]}
              onChange={(e) => onChange({ ...value, [k]: Number(e.target.value) })} />
            <span className="muted small nowrap">{Math.round((100 * value[k]) / sum)}% <Info>{x.priorities}</Info></span>
          </label>
        ))}
      </div>
    </Card>
  )
}
