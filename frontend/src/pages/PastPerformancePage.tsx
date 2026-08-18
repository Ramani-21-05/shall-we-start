// src/pages/PastPerformancePage.tsx
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { fetchHistoricalAnalytics } from '@/api/history'
import { fetchChampionModel } from '@/api/models'
import { DRUGS } from '@/types'
import {
  History, TrendingUp, BarChart3, Calendar, Activity,
  ArrowUpRight, ArrowDownRight, Minus,
} from 'lucide-react'
import {
  LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Legend, ReferenceLine, Cell,
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

const YEAR_COLORS: Record<string, string> = {
  '2014': '#6366f1',
  '2015': '#22d3ee',
  '2016': '#f59e0b',
  '2017': '#10b981',
  '2018': '#f87171',
  '2019': '#a78bfa',
}

const TOOLTIP_STYLE = {
  background: '#ffffff',
  border: '1px solid #cbd5e1',
  borderRadius: '0.75rem',
  color: '#0f172a',
  fontSize: 12,
  boxShadow: '0 10px 25px -5px rgba(15, 23, 42, 0.1)',
}

function GrowthBadge({ pct }: { pct: number | null }) {
  if (pct === null) return <span className="text-slate-500 text-xs">—</span>
  const pos = pct >= 0
  return (
    <span className={`inline-flex items-center gap-0.5 text-xs font-semibold ${pos ? 'text-emerald-400' : 'text-red-400'}`}>
      {pos ? <ArrowUpRight size={12} /> : <ArrowDownRight size={12} />}
      {Math.abs(pct).toFixed(1)}%
    </span>
  )
}

function StatCard({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="glass-card p-4 text-center">
      <p className="text-xl font-bold text-indigo-300 font-mono">{value}</p>
      {sub && <p className="text-xs text-slate-500 font-mono">{sub}</p>}
      <p className="text-xs text-slate-400 mt-1">{label}</p>
    </div>
  )
}

// Custom season bar that colors above/below 1.0 differently
function SeasonBar({ index }: { index: number }) {
  const pct = Math.min(Math.max(index * 50, 0), 100)
  const color = index >= 1.0 ? '#6366f1' : '#64748b'
  return (
    <div className="w-full bg-slate-800 rounded-full h-1.5 mt-1">
      <div className="h-1.5 rounded-full transition-all" style={{ width: `${pct}%`, background: color }} />
    </div>
  )
}

export function PastPerformancePage() {
  const [drug, setDrug] = useState('M01AB')

  const { data: hist, isLoading, isFetching } = useQuery({
    queryKey: ['history', drug],
    queryFn: () => fetchHistoricalAnalytics(drug),
    staleTime: Infinity,   // 2014-2019 data never changes — never re-fetch
    gcTime: Infinity,      // keep in React Query cache forever
  })
  const { data: championModel } = useQuery({
    queryKey: ['drug-champion', drug],
    queryFn: () => fetchChampionModel(drug),
  })

  const champion = championModel
  const s = hist?.summary

  // Build tick labels for the trend chart (show Jan of each year)
  const trendTicks = hist?.monthly_series
    .filter(p => p.month === 1)
    .map(p => p.label) ?? []

  return (
    <div className="space-y-6 animate-fade-in-up">
      {/* ── Header ── */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold gradient-text flex items-center gap-2">
            <History size={22} /> Past Performance
          </h1>
          <div className="flex items-center gap-3 mt-1 flex-wrap">
            <p className="text-slate-400 text-sm">
              Historical Sales Analysis · 2014–2019 · {DRUG_FULL_NAMES[drug]}
            </p>


          </div>
        </div>
        <select
          value={drug}
          onChange={e => setDrug(e.target.value)}
          className="glass-card-sm px-4 py-2 text-sm text-slate-900 bg-white border border-slate-300 cursor-pointer"
        >
          {DRUGS.map(d => (
            <option key={d} value={d} >{d}</option>
          ))}
        </select>
      </div>

      {(isLoading || isFetching) && !hist && (
        <div className="space-y-5">
          {/* KPI skeleton */}
          <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-6 gap-3">
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="glass-card p-4 text-center animate-pulse">
                <div className="h-6 bg-slate-700 rounded mb-2 mx-auto w-3/4" />
                <div className="h-3 bg-slate-800 rounded mx-auto w-1/2" />
              </div>
            ))}
          </div>
          {/* Bar chart skeleton */}
          <div className="glass-card p-5">
            <div className="h-4 bg-slate-700 rounded w-48 mb-4 animate-pulse" />
            <div className="grid grid-cols-6 gap-2 mb-4">
              {Array.from({ length: 6 }).map((_, i) => (
                <div key={i} className="animate-pulse">
                  <div className="h-5 bg-slate-700 rounded mb-1" />
                  <div className="h-3 bg-slate-800 rounded" />
                </div>
              ))}
            </div>
            <div className="h-48 bg-slate-800/50 rounded-lg animate-pulse flex items-end gap-2 px-4 pb-4">
              {[40, 30, 85, 95, 90, 80].map((h, i) => (
                <div key={i} className="flex-1 rounded-t" style={{ height: `${h}%`, background: Object.values(YEAR_COLORS)[i] + '33' }} />
              ))}
            </div>
          </div>
          {/* Trend chart skeleton */}
          <div className="glass-card p-5 animate-pulse">
            <div className="h-4 bg-slate-700 rounded w-64 mb-2" />
            <div className="h-3 bg-slate-800 rounded w-80 mb-4" />
            <div className="h-72 bg-slate-800/50 rounded-lg flex items-center justify-center">
              <div className="text-slate-600 text-sm">Loading 72-month trend…</div>
            </div>
          </div>
        </div>
      )}

      {s && (
        <>
          {/* ── KPI Strip ── */}
          <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-6 gap-3">
            <StatCard label="Total Sales (6 yrs)" value={s.overall_total.toLocaleString()} />
            <StatCard label="Avg Monthly Sales" value={s.overall_avg_monthly.toLocaleString()} />
            <StatCard label="Peak Monthly Sales" value={s.overall_max_monthly.toLocaleString()} sub={s.peak_month} />
            <StatCard label="Min Monthly Sales" value={s.overall_min_monthly.toLocaleString()} />
            <StatCard label="Model" value={champion?.model_name ?? '—'} sub={champion ? `RMSLE ${champion.rmsle?.toFixed(4)}` : undefined} />
            <StatCard label="Model MAE" value={champion?.mae != null ? champion.mae.toFixed(2) : '—'} sub={champion?.training_cutoff_date ? `Train: ${champion.training_cutoff_date}` : "2019 holdout"} />
          </div>

          {/* ── Annual Totals Bar ── */}
          <div className="glass-card p-5">
            <div className="flex items-center gap-2 mb-4">
              <BarChart3 size={16} className="text-indigo-400" />
              <p className="text-sm font-semibold text-white">Year-over-Year Annual Sales</p>
            </div>
            <div className="grid grid-cols-6 gap-2 mb-4">
              {hist!.yoy_series.map(y => (
                <div key={y.year} className="text-center">
                  <p className="text-base font-bold text-white font-mono">{y.total_sales.toLocaleString()}</p>
                  <p className="text-[11px] text-slate-400">{y.year}</p>
                  <GrowthBadge pct={y.growth_pct} />
                </div>
              ))}
            </div>
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={hist!.yoy_series} margin={{ top: 4, right: 12, left: 0, bottom: 4 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
                <XAxis dataKey="year" tick={{ fill: '#94a3b8', fontSize: 12 }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fill: '#334155', fontSize: 11, fontWeight: 600 }} axisLine={false} tickLine={false} width={60} />
                <Tooltip contentStyle={TOOLTIP_STYLE} formatter={(v: any) => [Number(v).toLocaleString(), 'Annual Sales']} />
                <Bar dataKey="total_sales" radius={[4, 4, 0, 0]} maxBarSize={60}>
                  {hist!.yoy_series.map(entry => (
                    <Cell key={entry.year} fill={YEAR_COLORS[String(entry.year)] ?? '#6366f1'} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* ── Full Trend Chart ── */}
          <div className="glass-card p-5">
            <div className="flex items-center gap-2 mb-1">
              <TrendingUp size={16} className="text-cyan-400" />
              <p className="text-sm font-semibold text-white">Monthly Sales Trend · 2014–2019</p>
            </div>
            <p className="text-xs text-slate-500 mb-4">72 months of raw hourly data aggregated to monthly totals</p>
            <ResponsiveContainer width="100%" height={280}>
              <LineChart data={hist!.monthly_series} margin={{ top: 4, right: 12, left: 0, bottom: 4 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis
                  dataKey="label"
                  tick={{ fill: '#334155', fontSize: 10, fontWeight: 600 }}
                  ticks={trendTicks}
                  tickFormatter={v => v.slice(0, 4)}
                  axisLine={{ stroke: 'rgba(255,255,255,0.1)' }}
                  tickLine={false}
                />
                <YAxis tick={{ fill: '#334155', fontSize: 11, fontWeight: 600 }} axisLine={false} tickLine={false} width={55} />
                <Tooltip
                  contentStyle={TOOLTIP_STYLE}
                  formatter={(v: any) => [Number(v).toLocaleString(), 'Monthly Sales']}
                  labelFormatter={l => `Period: ${l}`}
                />
                {/* Year boundary reference lines */}
                {['2015-01', '2016-01', '2017-01', '2018-01', '2019-01'].map(yr => (
                  <ReferenceLine key={yr} x={yr} stroke="rgba(255,255,255,0.08)" strokeDasharray="4 2" />
                ))}
                <Line
                  type="monotone"
                  dataKey="total_sales"
                  stroke="#6366f1"
                  strokeWidth={2}
                  dot={false}
                  name="Monthly Sales"
                  activeDot={{ r: 4, fill: '#a5b4fc' }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>

          {/* ── YoY Monthly Grouped Bar ── */}
          <div className="glass-card p-5">
            <div className="flex items-center gap-2 mb-1">
              <Activity size={16} className="text-emerald-400" />
              <p className="text-sm font-semibold text-white">Year-over-Year Monthly Breakdown</p>
            </div>
            <p className="text-xs text-slate-500 mb-4">
              Each month's sales per year — spot seasonal shifts across 2014–2019
            </p>
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={hist!.yoy_monthly} margin={{ top: 4, right: 8, left: 0, bottom: 4 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
                <XAxis dataKey="month_name" tick={{ fill: '#334155', fontSize: 11, fontWeight: 600 }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fill: '#334155', fontSize: 10, fontWeight: 600 }} axisLine={false} tickLine={false} width={50} />
                <Tooltip contentStyle={TOOLTIP_STYLE} formatter={(v: any, name: any) => [Number(v).toLocaleString(), name]} />
                <Legend wrapperStyle={{ fontSize: 11, color: '#94a3b8', paddingTop: 4 }} />
                {['2014', '2015', '2016', '2017', '2018', '2019'].map(yr => (
                  <Bar key={yr} dataKey={yr} fill={YEAR_COLORS[yr]} maxBarSize={16} radius={[2, 2, 0, 0]} />
                ))}
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* ── Annual Totals Table ── */}
          <div className="glass-card p-5">
            <div className="flex items-center gap-2 mb-4">
              <Minus size={16} className="text-slate-400" />
              <p className="text-sm font-semibold text-white">Annual Sales Summary · {drug}</p>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-slate-500 text-xs uppercase tracking-wider border-b border-white/5">
                    <th className="text-left py-2 px-3">Year</th>
                    <th className="text-right py-2 px-3">Annual Total</th>
                    <th className="text-right py-2 px-3">Avg/Month</th>
                    <th className="text-right py-2 px-3">YoY Growth</th>
                    <th className="text-right py-2 px-3">% of 6-yr Total</th>
                  </tr>
                </thead>
                <tbody>
                  {hist!.yoy_series.map((y, i) => {
                    const avgMonth = y.total_sales / 12
                    const pctTotal = s.overall_total > 0 ? (y.total_sales / s.overall_total * 100) : 0
                    return (
                      <tr key={y.year} className="border-b border-white/5 hover:bg-white/5 transition-colors">
                        <td className="py-3 px-3">
                          <span
                            className="inline-block w-2 h-2 rounded-full mr-2"
                            style={{ background: YEAR_COLORS[String(y.year)] }}
                          />
                          <span className="font-semibold text-white">{y.year}</span>
                        </td>
                        <td className="py-3 px-3 text-right font-mono text-slate-200">
                          {y.total_sales.toLocaleString()}
                        </td>
                        <td className="py-3 px-3 text-right font-mono text-slate-400">
                          {avgMonth.toFixed(1)}
                        </td>
                        <td className="py-3 px-3 text-right">
                          <GrowthBadge pct={y.growth_pct} />
                        </td>
                        <td className="py-3 px-3 text-right">
                          <div className="flex items-center justify-end gap-2">
                            <div className="w-16 bg-slate-800 rounded-full h-1.5">
                              <div
                                className="h-1.5 rounded-full"
                                style={{ width: `${pctTotal}%`, background: YEAR_COLORS[String(y.year)] }}
                              />
                            </div>
                            <span className="text-slate-400 text-xs w-10 text-right">{pctTotal.toFixed(1)}%</span>
                          </div>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
                <tfoot>
                  <tr className="border-t border-white/10">
                    <td className="py-3 px-3 text-xs text-slate-500 font-semibold uppercase tracking-wide">
                      6-Year Total
                    </td>
                    <td className="py-3 px-3 text-right font-mono font-bold text-indigo-300">
                      {s.overall_total.toLocaleString()}
                    </td>
                    <td className="py-3 px-3 text-right font-mono text-slate-400">
                      {s.overall_avg_monthly.toFixed(1)}
                    </td>
                    <td colSpan={2} />
                  </tr>
                </tfoot>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  )
}

