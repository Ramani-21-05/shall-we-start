// src/pages/ForecastPage.tsx
import { useState, useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { fetchForecast, retrainModel, fetchRetrainEligibility } from '@/api/forecast'
import { DRUGS } from '@/types'
import {
  ComposedChart, Area, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Legend,
} from 'recharts'
import { TrendingUp, Calendar, RefreshCw, Database, Cpu, Zap, AlertCircle } from 'lucide-react'

type Granularity = 'daily' | 'weekly' | 'monthly'
type YearFilter = '2019' | '2020'

export function ForecastPage() {
  const [drug, setDrug] = useState('M01AB')
  const [granularity, setGranularity] = useState<Granularity>('daily')
  const [yearFilter, setYearFilter] = useState<YearFilter>('2019')
  const [isRetraining, setIsRetraining] = useState(false)
  const [retrainNotice, setRetrainNotice] = useState<string | null>(null)

  // Query live eligibility — staleTime: 0 ensures fresh check on reload
  const { data: eligibility, refetch: refetchEligibility } = useQuery({
    queryKey: ['retrain-eligibility', drug],
    queryFn: () => fetchRetrainEligibility(drug),
    staleTime: 0,
    refetchInterval: 5_000,
  })

  const { data, isLoading, isFetching, refetch } = useQuery({
    queryKey: ['forecast', drug, yearFilter],
    queryFn: () => fetchForecast(drug, yearFilter),
    staleTime: 0, // Fetch fresh data from Supabase
  })

  const handleRetrain = async () => {
    try {
      setIsRetraining(true)
      setRetrainNotice(`⚡ Retraining all 8 drug models on 3 months of new actual sales (is_training = false)... Syncing to Supabase forecast_results.`)
      await retrainModel(drug)

      let attempts = 0
      const pollInterval = setInterval(async () => {
        attempts++
        const elRes = await refetchEligibility()
        refetch()
        if (!elRes.data?.eligible || attempts >= 10) {
          clearInterval(pollInterval)
          setIsRetraining(false)
          setRetrainNotice(`✅ Model Retraining Complete for all 8 drugs! Updated forecasts saved to forecast_results and is_training set to True.`)
          setTimeout(() => {
            setRetrainNotice(null)
          }, 7500)
        }
      }, 1500)
    } catch (err) {
      setIsRetraining(false)
      setRetrainNotice(`❌ Retrain error: ${err instanceof Error ? err.message : 'Unknown error'}`)
      setTimeout(() => {
        setRetrainNotice(null)
      }, 5000)
    }
  }

  // Aggregate forecast data dynamically into Daily, Weekly, or Monthly resolution
  const chartData = useMemo(() => {
    if (!data || data.length === 0) return []

    if (granularity === 'daily') {
      return data.map(d => ({
        date: d.date,
        actual: d.actual_sales != null && !isNaN(d.actual_sales) ? Number(d.actual_sales.toFixed(1)) : null,
        p50: d.p50_demand != null ? Number(d.p50_demand.toFixed(1)) : null,
        p10: d.p10_demand != null ? Number(d.p10_demand.toFixed(1)) : null,
        p90: d.p90_demand != null ? Number(d.p90_demand.toFixed(1)) : null,
      }))
    }

    if (granularity === 'weekly') {
      const weeks: Record<string, { actualSum: number; p50Sum: number; p10Sum: number; p90Sum: number; count: number; startDate: string; hasActual: boolean }> = {}

      data.forEach((d, idx) => {
        const weekNum = Math.floor(idx / 7) + 1
        const key = `W${weekNum < 10 ? '0' : ''}${weekNum}`

        if (!weeks[key]) {
          weeks[key] = { actualSum: 0, p50Sum: 0, p10Sum: 0, p90Sum: 0, count: 0, startDate: d.date, hasActual: false }
        }

        if (d.actual_sales != null) {
          weeks[key].actualSum += d.actual_sales
          weeks[key].hasActual = true
        }
        weeks[key].p50Sum += d.p50_demand ?? 0
        weeks[key].p10Sum += d.p10_demand ?? 0
        weeks[key].p90Sum += d.p90_demand ?? 0
        weeks[key].count += 1
      })

      return Object.entries(weeks).map(([wKey, wData]) => ({
        date: `${wKey} (${wData.startDate.slice(5)})`,
        actual: wData.hasActual ? Number(wData.actualSum.toFixed(1)) : null,
        p50: Number(wData.p50Sum.toFixed(1)),
        p10: Number(wData.p10Sum.toFixed(1)),
        p90: Number(wData.p90Sum.toFixed(1)),
      }))
    }

    // Monthly View: Group by YYYY-MM
    const months: Record<string, { actualSum: number; p50Sum: number; p10Sum: number; p90Sum: number; count: number; hasActual: boolean }> = {}

    data.forEach(d => {
      const monthKey = d.date.slice(0, 7)

      if (!months[monthKey]) {
        months[monthKey] = { actualSum: 0, p50Sum: 0, p10Sum: 0, p90Sum: 0, count: 0, hasActual: false }
      }

      if (d.actual_sales != null) {
        months[monthKey].actualSum += d.actual_sales
        months[monthKey].hasActual = true
      }
      months[monthKey].p50Sum += d.p50_demand ?? 0
      months[monthKey].p10Sum += d.p10_demand ?? 0
      months[monthKey].p90Sum += d.p90_demand ?? 0
      months[monthKey].count += 1
    })

    return Object.entries(months).map(([mKey, mData]) => ({
      date: mKey,
      actual: mData.hasActual ? Number(mData.actualSum.toFixed(1)) : null,
      p50: Number(mData.p50Sum.toFixed(1)),
      p10: Number(mData.p10Sum.toFixed(1)),
      p90: Number(mData.p90Sum.toFixed(1)),
    }))
  }, [data, granularity])

  // Count distinct months with actual_sales in raw data (used for 2020 threshold gate)
  const monthsWithActuals = useMemo(() => {
    if (!data || data.length === 0) return 0
    const months = new Set(
      data
        .filter(d => d.actual_sales != null)
        .map(d => d.date.slice(0, 7))
    )
    return months.size
  }, [data])

  // 2019: show if any actuals exist in current view
  // 2020: only show once 9+ months of actual data are available
  const ACTUAL_LINE_THRESHOLD = 9
  const showActualLine = useMemo(() => {
    if (yearFilter === '2019') return chartData.some(d => d.actual != null)
    return monthsWithActuals >= ACTUAL_LINE_THRESHOLD
  }, [chartData, yearFilter, monthsWithActuals])

  // Custom Y-Axis tick steps of 8
  const yTicks = useMemo(() => {
    if (granularity !== 'daily' || !chartData || chartData.length === 0) return undefined

    let maxVal = 0
    chartData.forEach(d => {
      if (d.actual != null && d.actual > maxVal) maxVal = d.actual
      if (d.p90 != null && d.p90 > maxVal) maxVal = d.p90
    })

    const step = 8
    const top = Math.ceil((maxVal + 2) / step) * step
    const ticks: number[] = []
    for (let val = 0; val <= top; val += step) {
      ticks.push(val)
    }
    return ticks
  }, [chartData, granularity])

  const totalP50 = useMemo(() => {
    if (!chartData || chartData.length === 0) return '0'
    const sum = chartData.reduce((s, c) => s + (c.p50 ?? 0), 0)
    return granularity === 'daily'
      ? (sum / chartData.length).toFixed(1)
      : Math.round(sum).toLocaleString()
  }, [chartData, granularity])

  return (
    <div className="space-y-6 animate-fade-in-up">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold gradient-text flex items-center gap-2">
            <TrendingUp size={22} /> Demand Forecast
          </h1>
          <p className="text-slate-400 text-sm mt-1">
            {yearFilter === '2019' ? '2019 Holdout Backtest · P10 / P50 / P90 Prediction Intervals' : '2020 Operational Demand Projection · Pure Predictive AI Horizon'}
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          {/* Year Selection Toggle */}
          <div className="glass-card-sm p-1 flex items-center gap-1 border border-indigo-500/30">
            {(['2019', '2020'] as YearFilter[]).map(y => (
              <button
                key={y}
                onClick={() => setYearFilter(y)}
                className={`px-3 py-1.5 rounded-lg text-xs font-bold uppercase tracking-wider transition-all cursor-pointer ${yearFilter === y
                    ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/40 border border-indigo-400/30'
                    : 'text-slate-400 hover:text-white hover:bg-white/5'
                  }`}
              >
                {y === '2019' ? '2019 Holdout' : '2020 Forecast'}
              </button>
            ))}
          </div>

          {/* On-Demand Retrain Button — shown when 3+ months of actual data are untrained (is_training = false) */}
          {eligibility?.eligible && (
            <button
              onClick={handleRetrain}
              disabled={isRetraining}
              className="glass-card-sm px-3.5 py-1.5 flex items-center gap-2 text-xs font-semibold text-amber-300 hover:text-amber-100 border border-amber-500/50 bg-amber-500/10 hover:bg-amber-600/30 cursor-pointer rounded-lg transition-all shadow-lg shadow-amber-500/20"
              title={`${eligibility.untrained_months} months of new actuals detected (is_training = false) — click to retrain model, update forecast_results, and set is_training = True`}
            >
              <Zap size={14} className={isRetraining ? 'animate-bounce text-amber-400' : 'text-amber-400 animate-pulse'} />
              <span>{isRetraining ? 'Retraining...' : '⚡ Retrain Model'}</span>
            </button>
          )}

          {/* Refresh Button */}
          <button
            onClick={() => refetch()}
            disabled={isFetching}
            className="glass-card-sm px-3 py-1.5 flex items-center gap-1.5 text-xs text-indigo-300 hover:text-white border border-indigo-500/30 hover:bg-indigo-600/20 cursor-pointer rounded-lg transition-all"
            title="Refetch live data from Supabase"
          >
            <RefreshCw size={14} className={isFetching ? 'animate-spin text-indigo-400' : ''} />
            <span>Sync</span>
          </button>

          {/* Daily / Weekly / Monthly Toggle Buttons */}
          <div className="glass-card-sm p-1 flex items-center gap-1 border border-indigo-500/20">
            {(['daily', 'weekly', 'monthly'] as Granularity[]).map(g => (
              <button
                key={g}
                onClick={() => setGranularity(g)}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold uppercase tracking-wider transition-all cursor-pointer ${granularity === g
                    ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/30'
                    : 'text-slate-400 hover:text-white hover:bg-white/5'
                  }`}
              >
                {g}
              </button>
            ))}
          </div>

          <DrugSelector value={drug} onChange={setDrug} />
        </div>
      </div>

      {/* Toast Notification Banner */}
      {retrainNotice && (
        <div className="p-3 bg-indigo-900/40 border border-indigo-500/40 rounded-xl text-xs text-indigo-200 flex items-center justify-between animate-fade-in">
          <div className="flex items-center gap-2">
            <Cpu size={16} className="text-amber-400 animate-pulse" />
            <span>{retrainNotice}</span>
          </div>
          <button onClick={() => setRetrainNotice(null)} className="text-indigo-400 hover:text-white font-bold px-2">✕</button>
        </div>
      )}

      {/* Retrain Available Banner */}
      {eligibility?.eligible && (
        <div className="p-3.5 bg-amber-500/15 border border-amber-500/40 rounded-xl text-xs text-amber-200 flex items-center justify-between animate-fade-in shadow-md">
          <div className="flex items-center gap-2.5">
            <Zap size={18} className="text-amber-400 shrink-0 animate-bounce" />
            <span>
              <strong>⚡ New 3 Months Data Available ({eligibility.untrained_months} months):</strong> Data where <code>is_training = false</code> ({eligibility.months.join(', ')}) is ready. Click <strong>⚡ Retrain Model</strong> above to train on the new data, update <code>forecast_results</code>, and return <code>is_training</code> to <code>True</code>.
            </span>
          </div>
          <button
            onClick={handleRetrain}
            disabled={isRetraining}
            className="ml-3 px-3 py-1 bg-amber-500 text-slate-950 font-bold rounded-md text-xs hover:bg-amber-400 transition-all shrink-0 cursor-pointer shadow"
          >
            {isRetraining ? 'Retraining...' : 'Retrain Now'}
          </button>
        </div>
      )}



      {/* Forecast Chart Card */}
      <div className="glass-card p-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <Calendar size={14} className="text-indigo-400" />
            <span className="text-xs text-slate-300 font-medium">
              {yearFilter === '2019' ? '2019 Holdout Resolution' : '2020 Operational Resolution'} ({chartData.length} {granularity} points)
            </span>
          </div>

          <div className="flex items-center gap-2">
            <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              <Database size={11} /> Supabase Live ({yearFilter})
            </span>
            <span className="badge badge-brand">
              {granularity.toUpperCase()} VIEW
            </span>
          </div>
        </div>

        {isLoading ? (
          <Spinner />
        ) : (
          <ResponsiveContainer width="100%" height={380}>
            <ComposedChart data={chartData}>
              <defs>
                <linearGradient id="bandGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#6366f1" stopOpacity={0.25} />
                  <stop offset="95%" stopColor="#6366f1" stopOpacity={0.03} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
              <XAxis dataKey="date" tick={{ fill: '#94a3b8', fontSize: 10 }} tickCount={granularity === 'monthly' ? 12 : 8}
                axisLine={{ stroke: 'rgba(255,255,255,0.1)' }} tickLine={false} />
              <YAxis
                ticks={yTicks}
                domain={yTicks ? [0, yTicks[yTicks.length - 1]] : undefined}
                tick={{ fill: '#94a3b8', fontSize: 11 }}
                axisLine={false}
                tickLine={false}
              />
              <Tooltip
                contentStyle={{ background: 'hsl(245 40% 12%)', border: '1px solid rgba(99,102,241,0.3)', borderRadius: '0.5rem', color: '#e2e8f0', fontSize: 12 }}
                labelStyle={{ color: '#818cf8', fontWeight: 600 }}
              />
              <Legend wrapperStyle={{ fontSize: 12, color: '#94a3b8' }} />
              {/* Uncertainty band */}
              <Area type="monotone" dataKey="p90" stroke="none" fill="url(#bandGrad)" name="P90 Upper Target" />
              <Area type="monotone" dataKey="p10" stroke="none" fill="hsl(245 40% 8%)" name="P10 Lean Floor" />
              <Line type="monotone" dataKey="p50" stroke="#6366f1" strokeWidth={2.5} dot={granularity !== 'daily'} name="P50 Forecast" />
              {/* Actual Sales line: always on 2019, only when 9+ months of actuals on 2020 */}
              {showActualLine && (
                <Line type="monotone" dataKey="actual" stroke="#10b981" strokeWidth={2} dot={granularity !== 'daily'} name="Actual Sales" />
              )}
            </ComposedChart>
          </ResponsiveContainer>
        )}

        {/* 2020: show progress toward the 9-month threshold */}
        {yearFilter === '2020' && !showActualLine && (
          <div className="mt-3 flex items-center gap-2 text-xs text-slate-400">
            <span className="text-amber-400">◑</span>
            <span>
              Actual sales line unlocks at <strong className="text-amber-300">9 months</strong> of ingested data —
              currently <strong className="text-indigo-300">{monthsWithActuals} / {ACTUAL_LINE_THRESHOLD}</strong> months available.
            </span>
          </div>
        )}
        {yearFilter === '2020' && showActualLine && (
          <div className="mt-3 flex items-center gap-2 text-xs text-emerald-400">
            <span>✅</span>
            <span><strong>{monthsWithActuals} months</strong> of actual data — Actual Sales line is now visible.</span>
          </div>
        )}
      </div>

      {/* Summary Stat Cards */}
      {data && (
        <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
          <StatCard
            label={granularity === 'daily' ? 'Total Days' : granularity === 'weekly' ? 'Total Weeks' : 'Total Months'}
            value={chartData.length}
          />
          <StatCard
            label={granularity === 'daily' ? 'Avg Daily P50' : 'Total Predicted P50 Demand'}
            value={totalP50}
          />
          <StatCard label="Year Mode" value={yearFilter === '2019' ? '2019 Holdout' : '2020 Operational'} />
          <StatCard label="Drug Category" value={drug} />
        </div>
      )}
    </div>
  )
}

function StatCard({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="glass-card p-4 text-center">
      <p className="text-xl font-bold text-indigo-300">{value}</p>
      <p className="text-xs text-slate-400 mt-1">{label}</p>
    </div>
  )
}

function DrugSelector({ value, onChange }: { value: string; onChange: (v: string) => void }) {
  return (
    <select
      value={value}
      onChange={e => onChange(e.target.value)}
      className="glass-card-sm px-4 py-2 text-sm text-white bg-slate-900/90 border-indigo-500/30 cursor-pointer rounded-lg"
    >
      {DRUGS.map(d => <option key={d} value={d} className="bg-slate-900">{d}</option>)}
    </select>
  )
}

function Spinner() {
  return (
    <div className="flex justify-center items-center h-64">
      <div className="w-10 h-10 rounded-full border-2 border-indigo-500 border-t-transparent animate-spin" />
    </div>
  )
}
