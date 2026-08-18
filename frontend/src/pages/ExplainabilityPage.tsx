// src/pages/ExplainabilityPage.tsx
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { fetchExplainabilitySummary, fetchShapWeights } from '@/api/explain'
import { fetchChampionModel } from '@/api/models'
import { DRUGS } from '@/types'
import { Lightbulb, Info, Award, Compass, Zap, ShieldCheck } from 'lucide-react'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Cell,
} from 'recharts'

const DRUG_FULL_NAMES: Record<string, string> = {
  M01AB: 'Anti-inflammatory (Acetic acid deriv.)',
  M01AE: 'Anti-inflammatory (Propionic acid deriv.)',
  N02BA: 'Analgesic & Antipyretic (Salicylic acid)',
  N02BE: 'Analgesic & Antipyretic (Pyrazolones)',
  N05B:  'Psycholeptics (Anxiolytics)',
  N05C:  'Psycholeptics (Hypnotics & Sedatives)',
  R03:   'Respiratory (Obstructive airway)',
  R06:   'Respiratory (Systemic Antihistamines)',
}

const DOMAIN_COLORS: Record<string, string> = {
  'Lag': '#6366f1',
  'Rolling': '#06b6d4',
  'Calendar': '#10b981',
  'EWMA': '#f59e0b',
  'Trend': '#a855f7',
  'Unknown': '#94a3b8',
}

export function ExplainabilityPage() {
  const [drug, setDrug] = useState('M01AB')

  const { data: summary, isLoading: isSummaryLoading } = useQuery({
    queryKey: ['explain-summary', drug],
    queryFn: () => fetchExplainabilitySummary(drug),
  })

  const { data: shapWeights, isLoading: isWeightsLoading } = useQuery({
    queryKey: ['shap-weights', drug],
    queryFn: () => fetchShapWeights(drug, 10),
  })

  const { data: championModel } = useQuery({
    queryKey: ['champion-model', drug],
    queryFn: () => fetchChampionModel(drug),
  })

  const isLoading = isSummaryLoading || isWeightsLoading

  const chartData = shapWeights?.map(d => ({
    feature: d.feature,
    shap: Number(d.mean_abs_shap.toFixed(4)),
    domain: d.feature_domain,
    gain: d.lgb_gain != null ? Math.round(d.lgb_gain) : null,
  })) ?? []

  const narrative = summary?.narrative

  return (
    <div className="space-y-6 animate-fade-in-up">
      {/* ── Header ── */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-black tracking-tight text-slate-900 flex items-center gap-2">
            <Lightbulb size={22} className="text-indigo-600" /> Model Explainability & Feature SHAP Analysis
          </h1>
          <p className="text-slate-500 text-sm mt-1 font-medium">
            Understanding why predictions occur · {DRUG_FULL_NAMES[drug]}
          </p>
        </div>
        <select
          value={drug}
          onChange={e => setDrug(e.target.value)}
          className="bg-white border border-slate-300 rounded-xl px-4 py-2 text-sm text-indigo-700 font-bold focus:outline-none focus:border-indigo-500 cursor-pointer shadow-sm"
        >
          {DRUGS.map(d => (
            <option key={d} value={d}>{d}</option>
          ))}
        </select>
      </div>

      {isLoading ? <Spinner /> : (
        <>
          {/* ── Active Model Summary Card ── */}
          <div className="max-w-md">
            <div className="p-5 rounded-2xl bg-white border border-slate-200 border-l-4 border-l-indigo-600 shadow-sm flex flex-col justify-between space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-indigo-600 uppercase tracking-wider flex items-center gap-1.5">
                  <Award size={14} /> Active Model
                </span>
                <span className="text-[10px] px-2.5 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200 font-bold font-mono">
                  CHAMPION
                </span>
              </div>
              <div>
                <p className="text-lg font-black text-slate-900">
                  {championModel?.model_name ?? 'LightGBM + SHAP'}
                </p>
                <p className="text-xs text-slate-500 mt-0.5 font-medium">
                  Holdout RMSLE: <span className="font-mono text-indigo-600 font-bold">{championModel?.rmsle?.toFixed(4) ?? '0.5014'}</span> · MAE: <span className="font-mono text-cyan-600 font-bold">{championModel?.mae?.toFixed(2) ?? '2.29'}</span>
                </p>
              </div>
              <p className="text-[11px] text-slate-400 font-medium">
                Evaluation: {championModel?.evaluation_set ?? '2019 Holdout'}
              </p>
            </div>
          </div>

          {/* ── Feature Domain Share Cards ── */}
          <div className="space-y-2">
            <p className="text-xs font-bold uppercase tracking-wider text-slate-500 flex items-center gap-1.5">
              <ShieldCheck size={14} className="text-emerald-600" /> Feature Domain Contribution Share
            </p>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              {summary?.domain_breakdown?.map(item => (
                <div key={item.domain} className="p-4 rounded-2xl bg-white border border-slate-200 shadow-sm relative overflow-hidden">
                  <div
                    className="absolute top-0 left-0 bottom-0 opacity-10"
                    style={{
                      width: `${item.percentage}%`,
                      background: DOMAIN_COLORS[item.domain] ?? '#6366f1'
                    }}
                  />
                  <div className="relative z-10 flex items-center justify-between">
                    <div>
                      <p className="text-xs font-semibold text-slate-600">{item.domain} Features</p>
                      <p className="text-xl font-black text-slate-900 font-mono mt-0.5">{item.percentage}%</p>
                    </div>
                    <span
                      className="w-3 h-3 rounded-full shadow-sm"
                      style={{ background: DOMAIN_COLORS[item.domain] ?? '#6366f1' }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* ── SHAP Bar Chart ── */}
          <div className="p-6 rounded-2xl bg-white border border-slate-200 shadow-sm space-y-3">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-base font-bold text-slate-900">Top 10 Feature Importance (|SHAP| Values)</p>
                <p className="text-xs text-slate-500">Mean absolute SHAP value measures total contribution to predicted sales volume</p>
              </div>
            </div>

            <ResponsiveContainer width="100%" height={360}>
              <BarChart data={chartData} layout="vertical" barSize={18} margin={{ top: 5, right: 30, left: 40, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" horizontal={false} />
                <XAxis type="number" tick={{ fill: '#334155', fontSize: 11, fontWeight: 600 }} axisLine={false} tickLine={false} />
                <YAxis
                  type="category"
                  dataKey="feature"
                  width={140}
                  tick={{ fill: '#0f172a', fontSize: 12, fontWeight: 700, fontFamily: 'monospace' }}
                  axisLine={false}
                  tickLine={false}
                />
                <Tooltip
                  contentStyle={{ background: '#ffffff', border: '1px solid #cbd5e1', borderRadius: '0.75rem', color: '#0f172a', fontSize: 12, boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)' }}
                  formatter={(v, _, props) => [
                    `${v} (Domain: ${(props as any)?.payload?.domain})`,
                    'Mean |SHAP| Impact'
                  ]}
                />
                <Bar dataKey="shap" radius={[0, 4, 4, 0]}>
                  {chartData.map((d, i) => (
                    <Cell key={i} fill={DOMAIN_COLORS[d.domain] ?? '#6366f1'} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* ── Feature Importance Table ── */}
          <div className="rounded-2xl bg-white border border-slate-200 shadow-sm overflow-hidden">
            <div className="p-4 border-b border-slate-200 flex items-center justify-between">
              <p className="text-base font-bold text-slate-900">Feature Weight Breakdown Table</p>
              <p className="text-xs text-slate-500">Sorted by Mean |SHAP| Value</p>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-xs text-slate-700">
                <thead className="bg-slate-50 uppercase text-[10px] text-slate-500 tracking-wider font-bold border-b border-slate-200">
                  <tr>
                    <th className="px-5 py-3 text-left">Rank</th>
                    <th className="px-5 py-3 text-left">Feature Name</th>
                    <th className="px-5 py-3 text-left">Domain</th>
                    <th className="px-5 py-3 text-right">Mean |SHAP| Impact</th>
                    <th className="px-5 py-3 text-right">Tree Split Gain</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 font-mono">
                  {shapWeights?.map((f, i) => (
                    <tr key={i} className="hover:bg-slate-50/80 transition">
                      <td className="px-5 py-3 text-slate-500 font-bold">#{f.feature_rank}</td>
                      <td className="px-5 py-3 text-indigo-700 font-bold font-sans">{f.feature}</td>
                      <td className="px-5 py-3 font-sans">
                        <span
                          className="px-2.5 py-0.5 rounded-full text-[10px] font-bold text-slate-800"
                          style={{ background: (DOMAIN_COLORS[f.feature_domain] ?? '#6366f1') + '22', border: `1px solid ${DOMAIN_COLORS[f.feature_domain] ?? '#6366f1'}44` }}
                        >
                          {f.feature_domain}
                        </span>
                      </td>
                      <td className="px-5 py-3 text-right text-emerald-600 font-bold">{f.mean_abs_shap.toFixed(5)}</td>
                      <td className="px-5 py-3 text-right text-slate-500">{f.lgb_gain != null ? Math.round(f.lgb_gain).toLocaleString() : '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  )
}

function Spinner() {
  return (
    <div className="flex justify-center items-center h-48">
      <div className="w-10 h-10 rounded-full border-2 border-indigo-500 border-t-transparent animate-spin" />
    </div>
  )
}

