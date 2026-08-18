// src/pages/Dashboard.tsx
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { fetchSalesAnalytics } from '@/api/dashboard'
import { DRUGS } from '@/types'
import {
  TrendingUp, Clock, Calendar, Award, BarChart3, PieChart as PieChartIcon,
  Filter, Sparkles, Activity, Layers, ShoppingBag, AlertCircle,
} from 'lucide-react'
import {
  AreaChart, Area, BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend, ReferenceLine,
} from 'recharts'

const DRUG_FULL_NAMES: Record<string, string> = {
  ALL:   'All 8 Categories Combined',
  M01AB: 'Anti-inflammatory (Acetic acid deriv.)',
  M01AE: 'Anti-inflammatory (Propionic acid deriv.)',
  N02BA: 'Analgesic & Antipyretic (Salicylic acid)',
  N02BE: 'Analgesic & Antipyretic (Pyrazolones)',
  N05B:  'Psycholeptics (Anxiolytics)',
  N05C:  'Psycholeptics (Hypnotics & Sedatives)',
  R03:   'Respiratory (Obstructive airway)',
  R06:   'Respiratory (Systemic Antihistamines)',
}

const DRUG_COLORS: Record<string, string> = {
  M01AB: '#3b82f6',
  M01AE: '#06b6d4',
  N02BA: '#10b981',
  N02BE: '#f59e0b',
  N05B:  '#6366f1',
  N05C:  '#8b5cf6',
  R03:   '#f43f5e',
  R06:   '#14b8a6',
}

const TOOLTIP_STYLE = {
  background: '#ffffff',
  border: '1px solid #cbd5e1',
  borderRadius: '0.75rem',
  color: '#0f172a',
  fontSize: 12,
  boxShadow: '0 10px 25px -5px rgba(15, 23, 42, 0.1)',
}

const YEARS = ['ALL', '2014', '2015', '2016', '2017', '2018', '2019']

export function Dashboard() {
  const [selectedDrug, setSelectedDrug] = useState('ALL')
  const [selectedYear, setSelectedYear] = useState('ALL')
  const [trendView, setTrendView] = useState<'total' | 'stacked'>('total')

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['sales-analytics', selectedDrug, selectedYear],
    queryFn: () => fetchSalesAnalytics(selectedDrug, selectedYear),
    staleTime: 5 * 60 * 1000,
  })

  if (isLoading) return <LoadingState />
  if (isError || !data) return <ErrorState onRetry={() => refetch()} />
  if (data.error) return <div className="p-8 text-center text-red-400 glass-card">Error loading dashboard data: {data.error}</div>

  const { summary, combined_trend, seasonality, hourly_pattern, weekday_pattern, yoy_series, drug_shares } = data

  return (
    <div className="space-y-6 animate-fade-in-up">
      {/* ── Page Header & Controls ── */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 glass-card p-5">
        <div>
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-indigo-500/20 border border-indigo-500/30 flex items-center justify-center">
              <Activity className="text-indigo-400" size={18} />
            </div>
            <h1 className="text-2xl font-bold gradient-text">Sales & Demand Analytics Dashboard</h1>
          </div>
          <p className="text-slate-400 text-xs mt-1">
            Portfolio trend, seasonality, peak hours & weekdays across 50,000+ hourly pharmacy transaction records
          </p>
        </div>

        {/* Filters */}
        <div className="flex items-center flex-wrap gap-3">
          <div className="flex items-center gap-2 glass-card-sm px-3 py-1.5">
            <Filter size={14} className="text-indigo-400" />
            <span className="text-xs text-slate-400 font-medium">Category:</span>
            <select
              value={selectedDrug}
              onChange={e => setSelectedDrug(e.target.value)}
              className="bg-transparent text-xs text-white font-semibold cursor-pointer focus:outline-none"
            >
              <option value="ALL" className="bg-slate-900">All Drugs Combined</option>
              {DRUGS.map(d => (
                <option key={d} value={d} className="bg-slate-900">{d} - {DRUG_FULL_NAMES[d]}</option>
              ))}
            </select>
          </div>

          <div className="flex items-center gap-2 glass-card-sm px-3 py-1.5">
            <Calendar size={14} className="text-cyan-400" />
            <span className="text-xs text-slate-400 font-medium">Year:</span>
            <select
              value={selectedYear}
              onChange={e => setSelectedYear(e.target.value)}
              className="bg-transparent text-xs text-white font-semibold cursor-pointer focus:outline-none"
            >
              <option value="ALL" className="bg-slate-900">All Years (2014–2019)</option>
              {YEARS.filter(y => y !== 'ALL').map(y => (
                <option key={y} value={y} className="bg-slate-900">{y}</option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* ── Key Performance Highlight Cards Strip ── */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
        {/* Total Combined Sales */}
        <div className="glass-card p-4 border border-indigo-500/20 relative overflow-hidden">
          <div className="flex items-center justify-between">
            <p className="text-xs text-slate-400">Total Sales Volume</p>
            <div className="p-1.5 rounded-lg bg-indigo-500/10 text-indigo-400">
              <ShoppingBag size={16} />
            </div>
          </div>
          <p className="text-2xl font-bold text-indigo-300 font-mono mt-2">
            {summary.total_sales.toLocaleString()} <span className="text-xs font-normal text-slate-400">units</span>
          </p>
          <p className="text-[11px] text-slate-400 mt-1">
            Avg: <span className="text-indigo-400 font-semibold">{summary.avg_daily_sales.toLocaleString()}</span> / day
          </p>
        </div>

        {/* Peak Selling Month */}
        <div className="glass-card p-4 border border-emerald-500/20 relative overflow-hidden">
          <div className="flex items-center justify-between">
            <p className="text-xs text-slate-400">Peak Selling Month</p>
            <div className="p-1.5 rounded-lg bg-emerald-500/10 text-emerald-400">
              <Calendar size={16} />
            </div>
          </div>
          <p className="text-2xl font-bold text-emerald-400 mt-2">
            {summary.peak_month.month_name}
          </p>
          <p className="text-[11px] text-slate-400 mt-1">
            Avg: <span className="text-emerald-400 font-semibold">{summary.peak_month.avg_sales}</span> units/hr
          </p>
        </div>

        {/* Peak Day of Week */}
        <div className="glass-card p-4 border border-cyan-500/20 relative overflow-hidden">
          <div className="flex items-center justify-between">
            <p className="text-xs text-slate-400">Peak Day of Week</p>
            <div className="p-1.5 rounded-lg bg-cyan-500/10 text-cyan-400">
              <BarChart3 size={16} />
            </div>
          </div>
          <p className="text-2xl font-bold text-cyan-400 mt-2">
            {summary.peak_weekday.weekday}
          </p>
          <p className="text-[11px] text-slate-400 mt-1">
            Avg: <span className="text-cyan-400 font-semibold">{summary.peak_weekday.avg_sales}</span> units/hr
          </p>
        </div>

        {/* Peak Store Hour */}
        <div className="glass-card p-4 border border-amber-500/20 relative overflow-hidden">
          <div className="flex items-center justify-between">
            <p className="text-xs text-slate-400">Peak Store Hour</p>
            <div className="p-1.5 rounded-lg bg-amber-500/10 text-amber-400">
              <Clock size={16} />
            </div>
          </div>
          <p className="text-2xl font-bold text-amber-400 mt-2 font-mono">
            {summary.peak_hour.label}
          </p>
          <p className="text-[11px] text-slate-400 mt-1">
            Avg: <span className="text-amber-400 font-semibold">{summary.peak_hour.avg_sales}</span> units/hr
          </p>
        </div>

        {/* Top Drug Category */}
        <div className="glass-card p-4 border border-purple-500/20 relative overflow-hidden">
          <div className="flex items-center justify-between">
            <p className="text-xs text-slate-400">Top Performing Drug</p>
            <div className="p-1.5 rounded-lg bg-purple-500/10 text-purple-400">
              <Award size={16} />
            </div>
          </div>
          <p className="text-2xl font-bold text-purple-300 mt-2">
            {summary.top_drug?.drug_code ?? 'N02BE'}
          </p>
          <p className="text-[11px] text-slate-400 mt-1">
            Share: <span className="text-purple-400 font-semibold">{summary.top_drug?.percentage_share}%</span> of total
          </p>
        </div>
      </div>

      {/* ── Main Combined Trend Chart ── */}
      <div className="glass-card p-5 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div>
            <h2 className="text-base font-semibold text-white flex items-center gap-2">
              <TrendingUp className="text-indigo-400" size={18} />
              {selectedDrug === 'ALL' ? 'All Drugs Combined Sales Trend' : `${selectedDrug} Sales Trend`}
            </h2>
            <p className="text-xs text-slate-400">
              {selectedYear === 'ALL' ? '72-Month Historical Trajectory (2014–2019)' : `Monthly Trend for ${selectedYear}`}
            </p>
          </div>

          {selectedDrug === 'ALL' && (
            <div className="flex items-center gap-1 bg-slate-900/60 p-1 rounded-lg border border-white/5 self-start">
              <button
                onClick={() => setTrendView('total')}
                className={`px-3 py-1 text-xs rounded-md font-medium transition-all ${
                  trendView === 'total' ? 'bg-indigo-600 text-white shadow-md' : 'text-slate-400 hover:text-white'
                }`}
              >
                Combined Total
              </button>
              <button
                onClick={() => setTrendView('stacked')}
                className={`px-3 py-1 text-xs rounded-md font-medium transition-all ${
                  trendView === 'stacked' ? 'bg-indigo-600 text-white shadow-md' : 'text-slate-400 hover:text-white'
                }`}
              >
                Category Stack
              </button>
            </div>
          )}
        </div>

        <ResponsiveContainer width="100%" height={320}>
          {trendView === 'total' || selectedDrug !== 'ALL' ? (
            <AreaChart data={combined_trend} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id="colorTotal" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#6366f1" stopOpacity={0.4} />
                  <stop offset="95%" stopColor="#6366f1" stopOpacity={0.0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
              <XAxis dataKey="label" tick={{ fill: '#94a3b8', fontSize: 11 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: '#94a3b8', fontSize: 11 }} axisLine={false} tickLine={false} width={50} />
              <Tooltip
                contentStyle={TOOLTIP_STYLE}
                formatter={(v: number) => [v.toLocaleString(), 'Sales Units']}
                labelFormatter={l => `Period: ${l}`}
              />
              <Area
                type="monotone"
                dataKey="total_sales"
                stroke="#6366f1"
                strokeWidth={2.5}
                fillOpacity={1}
                fill="url(#colorTotal)"
                name="Combined Sales"
              />
            </AreaChart>
          ) : (
            <AreaChart data={combined_trend} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
              <XAxis dataKey="label" tick={{ fill: '#94a3b8', fontSize: 11 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: '#94a3b8', fontSize: 11 }} axisLine={false} tickLine={false} width={50} />
              <Tooltip contentStyle={TOOLTIP_STYLE} />
              <Legend wrapperStyle={{ fontSize: 11, paddingTop: 6 }} />
              {DRUGS.map(drug => (
                <Area
                  key={drug}
                  type="monotone"
                  dataKey={drug}
                  stackId="1"
                  stroke={DRUG_COLORS[drug]}
                  fill={DRUG_COLORS[drug]}
                  fillOpacity={0.6}
                  name={drug}
                />
              ))}
            </AreaChart>
          )}
        </ResponsiveContainer>
      </div>

      {/* ── Side-by-Side Peak Analysis: Peak Hour & Peak Weekday ── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {/* Peak Store Hour (24-Hour Distribution) */}
        <div className="glass-card p-5 space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Clock className="text-amber-400" size={18} />
              <div>
                <h3 className="text-sm font-semibold text-white">Peak Store Hour Analysis</h3>
                <p className="text-[11px] text-slate-400">Average sales volume by hour of day (00:00 to 23:00)</p>
              </div>
            </div>
            <span className="text-xs px-2.5 py-1 rounded-full font-bold bg-amber-500/10 text-amber-400 border border-amber-500/20">
              Peak: {summary.peak_hour.formatted}
            </span>
          </div>

          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={hourly_pattern} margin={{ top: 10, right: 5, left: -15, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
              <XAxis dataKey="hour" tick={{ fill: '#94a3b8', fontSize: 10 }} tickFormatter={h => `${h}h`} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: '#94a3b8', fontSize: 10 }} axisLine={false} tickLine={false} />
              <Tooltip
                contentStyle={TOOLTIP_STYLE}
                formatter={(val: any) => [`${(val ?? 0).toFixed(2)} units/hr`, 'Avg Sales']}
                labelFormatter={h => `Time Window: ${h}:00 - ${h}:59`}
              />
              <Bar dataKey="avg_sales" radius={[4, 4, 0, 0]}>
                {hourly_pattern.map(entry => (
                  <Cell
                    key={entry.hour}
                    fill={entry.hour === summary.peak_hour.hour ? '#f59e0b' : '#334155'}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Peak Weekday Analysis (7 Days) */}
        <div className="glass-card p-5 space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <BarChart3 className="text-cyan-400" size={18} />
              <div>
                <h3 className="text-sm font-semibold text-white">Peak Day of Week Analysis</h3>
                <p className="text-[11px] text-slate-400">Average sales volume by weekday (Monday to Sunday)</p>
              </div>
            </div>
            <span className="text-xs px-2.5 py-1 rounded-full font-bold bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
              Peak: {summary.peak_weekday.weekday}
            </span>
          </div>

          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={weekday_pattern} margin={{ top: 10, right: 5, left: -15, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
              <XAxis dataKey="short_name" tick={{ fill: '#94a3b8', fontSize: 11 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: '#94a3b8', fontSize: 10 }} axisLine={false} tickLine={false} />
              <Tooltip
                contentStyle={TOOLTIP_STYLE}
                formatter={(val: any) => [`${(val ?? 0).toFixed(2)} units/hr`, 'Avg Sales']}
              />
              <Bar dataKey="avg_sales" radius={[4, 4, 0, 0]}>
                {weekday_pattern.map(entry => (
                  <Cell
                    key={entry.weekday}
                    fill={entry.weekday === summary.peak_weekday.weekday ? '#06b6d4' : '#334155'}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* ── Seasonality & YoY Monthly Comparison ── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {/* Seasonality Pattern */}
        <div className="glass-card p-5 space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Calendar className="text-emerald-400" size={18} />
              <div>
                <h3 className="text-sm font-semibold text-white">Monthly Seasonality</h3>
                <p className="text-[11px] text-slate-400">Calendar month averages across all years</p>
              </div>
            </div>
            <span className="text-xs px-2.5 py-1 rounded-full font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              Peak: {summary.peak_month.month_name}
            </span>
          </div>

          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={seasonality} margin={{ top: 10, right: 5, left: -15, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
              <XAxis dataKey="month_name" tick={{ fill: '#94a3b8', fontSize: 11 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: '#94a3b8', fontSize: 10 }} axisLine={false} tickLine={false} />
              <Tooltip
                contentStyle={TOOLTIP_STYLE}
                formatter={(val: any, name: any) => [
                  name === 'index' ? (val ?? 0).toFixed(2) : `${(val ?? 0).toFixed(2)} units`,
                  name === 'index' ? 'Seasonal Index' : 'Avg Sales',
                ]}
              />
              <Bar dataKey="avg_sales" radius={[4, 4, 0, 0]}>
                {seasonality.map(entry => (
                  <Cell
                    key={entry.month}
                    fill={entry.index >= 1.0 ? '#10b981' : '#334155'}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* YoY Annual Growth */}
        <div className="glass-card p-5 space-y-3">
          <div className="flex items-center gap-2">
            <Layers className="text-indigo-400" size={18} />
            <div>
              <h3 className="text-sm font-semibold text-white">Year-over-Year Annual Growth</h3>
              <p className="text-[11px] text-slate-400">Total volume and percentage change per year</p>
            </div>
          </div>

          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={yoy_series} margin={{ top: 10, right: 5, left: -15, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
              <XAxis dataKey="year" tick={{ fill: '#94a3b8', fontSize: 11 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: '#94a3b8', fontSize: 10 }} axisLine={false} tickLine={false} />
              <Tooltip
                contentStyle={TOOLTIP_STYLE}
                formatter={(val: any) => [(val ?? 0).toLocaleString(), 'Annual Sales']}
              />
              <Bar dataKey="total_sales" fill="#6366f1" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* ── Drug Share & Distribution ── */}
      <div className="glass-card p-5 space-y-4">
        <div className="flex items-center gap-2">
          <PieChartIcon className="text-purple-400" size={18} />
          <div>
            <h3 className="text-sm font-semibold text-white">Category Revenue & Share Breakdown</h3>
            <p className="text-[11px] text-slate-400">Sales volume distribution among all 8 pharmaceutical categories</p>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-center">
          {/* Donut Chart */}
          <div className="h-[240px] flex items-center justify-center">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={drug_shares}
                  dataKey="total_sales"
                  nameKey="drug_code"
                  cx="50%"
                  cy="50%"
                  innerRadius={55}
                  outerRadius={90}
                  paddingAngle={3}
                >
                  {drug_shares.map(entry => (
                    <Cell key={entry.drug_code} fill={DRUG_COLORS[entry.drug_code] ?? '#6366f1'} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={TOOLTIP_STYLE}
                  formatter={(val: any, name: any) => [
                    `${(val ?? 0).toLocaleString()} units`,
                    DRUG_FULL_NAMES[name] || name,
                  ]}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>

          {/* Table Breakdown */}
          <div className="lg:col-span-2 overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-white/10 text-slate-400 text-left">
                  <th className="pb-2">Drug Code</th>
                  <th className="pb-2">Category Description</th>
                  <th className="pb-2 text-right">Total Units</th>
                  <th className="pb-2 text-right">Avg Monthly</th>
                  <th className="pb-2 text-right">Share %</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {drug_shares.map(item => (
                  <tr key={item.drug_code} className="hover:bg-white/5 transition-colors">
                    <td className="py-2.5 font-bold flex items-center gap-2">
                      <span className="w-2.5 h-2.5 rounded-full" style={{ background: DRUG_COLORS[item.drug_code] }} />
                      <span className="text-white font-mono">{item.drug_code}</span>
                    </td>
                    <td className="py-2.5 text-slate-300">{item.drug_name}</td>
                    <td className="py-2.5 text-right font-mono text-indigo-300 font-medium">
                      {item.total_sales.toLocaleString()}
                    </td>
                    <td className="py-2.5 text-right font-mono text-slate-400">
                      {item.avg_monthly_sales.toLocaleString()}
                    </td>
                    <td className="py-2.5 text-right font-mono font-bold text-purple-300">
                      {item.percentage_share}%
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* ── Strategic Demand Insights Card ── */}
      <div className="glass-card p-5 border border-indigo-500/20 bg-gradient-to-br from-indigo-950/20 to-slate-900/60">
        <div className="flex items-center gap-2 mb-3">
          <Sparkles className="text-indigo-400" size={18} />
          <h3 className="text-sm font-semibold text-white">Demand Intelligence Summary</h3>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs text-slate-300">
          <div className="glass-card-sm p-3 border-l-2 border-amber-400 space-y-1">
            <p className="font-semibold text-amber-300">Peak Store Hours (19:00 - 20:00)</p>
            <p className="text-slate-400">
              Demand spikes heavily between 7:00 PM and 8:00 PM. Pharmacy counter staffing and quick-pick inventory should be optimized for this 2-hour window.
            </p>
          </div>
          <div className="glass-card-sm p-3 border-l-2 border-cyan-400 space-y-1">
            <p className="font-semibold text-cyan-300">Weekend Volume Spike (Saturday)</p>
            <p className="text-slate-400">
              Saturdays record the highest average sales velocity of the week. Ensure Friday evening replenishment orders cover Saturday peak footfall.
            </p>
          </div>
          <div className="glass-card-sm p-3 border-l-2 border-emerald-400 space-y-1">
            <p className="font-semibold text-emerald-300">Winter Seasonality Peak (Jan/Oct)</p>
            <p className="text-slate-400">
              Pain relief (N02BE) and respiratory (R03) drugs show peak seasonal surges in winter months. Safety stock parameters should be increased by 20% starting October.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}

function LoadingState() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] space-y-4">
      <div className="w-12 h-12 rounded-full border-2 border-indigo-500 border-t-transparent animate-spin" />
      <p className="text-slate-400 text-xs animate-pulse font-medium">Loading sales analytics and demand patterns…</p>
    </div>
  )
}

function ErrorState({ onRetry }: { onRetry: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] text-center">
      <div className="glass-card p-6 max-w-md space-y-4">
        <AlertCircle size={36} className="text-amber-400 mx-auto" />
        <h2 className="text-white font-semibold text-base">Analytics Data Unavailable</h2>
        <p className="text-slate-400 text-xs">
          Could not fetch sales analytics from backend FastAPI server. Please check that backend is running on port 8000.
        </p>
        <button
          onClick={onRetry}
          className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-xs rounded-lg transition-all shadow-md"
        >
          Retry Connection
        </button>
      </div>
    </div>
  )
}
