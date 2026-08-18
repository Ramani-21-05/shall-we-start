// src/pages/StrategyPage.tsx
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { fetchStrategyOverview } from '@/api/strategy'
import { DRUGS } from '@/types'
import {
  Target, TrendingUp, Megaphone, Package, Award, Sparkles,
  ArrowUpRight, AlertCircle, ShoppingBag, ShieldCheck,
  CheckCircle2, Clock, Zap, Repeat, Layers, ChevronRight, Calendar,
} from 'lucide-react'

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

const MONTHS_LIST = [
  { num: 1, name: 'Jan' }, { num: 2, name: 'Feb' }, { num: 3, name: 'Mar' },
  { num: 4, name: 'Apr' }, { num: 5, name: 'May' }, { num: 6, name: 'Jun' },
  { num: 7, name: 'Jul' }, { num: 8, name: 'Aug' }, { num: 9, name: 'Sep' },
  { num: 10, name: 'Oct' }, { num: 11, name: 'Nov' }, { num: 12, name: 'Dec' },
]

const QUADRANT_COLORS = {
  PRIORITY:     { border: 'border-emerald-500/30', bg: 'bg-emerald-500/10', text: 'text-emerald-400', badge: 'bg-emerald-500/20 text-emerald-300' },
  EMERGING:     { border: 'border-cyan-500/30', bg: 'bg-cyan-500/10', text: 'text-cyan-400', badge: 'bg-cyan-500/20 text-cyan-300' },
  STABLE:       { border: 'border-amber-500/30', bg: 'bg-amber-500/10', text: 'text-amber-400', badge: 'bg-amber-500/20 text-amber-300' },
  LOW_PRIORITY: { border: 'border-red-500/30', bg: 'bg-red-500/10', text: 'text-red-400', badge: 'bg-red-500/20 text-red-300' },
}

export function StrategyPage() {
  const [selectedDrug, setSelectedDrug] = useState<string>('N02BE')
  const [selectedMonth, setSelectedMonth] = useState<number>(9) // Default Sep

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['strategy-overview', selectedMonth],
    queryFn: () => fetchStrategyOverview(selectedMonth),
    staleTime: 5 * 60 * 1000,
  })

  if (isLoading) return <LoadingState />
  if (isError || !data) return <ErrorState onRetry={() => refetch()} />

  const { summary, products, association_rules, campaign_timings } = data
  const selectedProduct = products.find(p => p.drug_code === selectedDrug) || products[0]

  // Quadrant groupings
  const priorityList = products.filter(p => p.quadrant === 'PRIORITY')
  const emergingList = products.filter(p => p.quadrant === 'EMERGING')
  const stableList   = products.filter(p => p.quadrant === 'STABLE')
  const lowList      = products.filter(p => p.quadrant === 'LOW_PRIORITY')

  return (
    <div className="space-y-6 animate-fade-in-up">
      {/* ── Page Header ── */}
      <div className="glass-card p-5 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-indigo-500/20 border border-indigo-500/30 flex items-center justify-center">
              <Target className="text-indigo-400" size={18} />
            </div>
            <h1 className="text-2xl font-bold gradient-text">Sales & Marketing Strategy Intelligence</h1>
          </div>
          <p className="text-slate-400 text-xs mt-1">
            Explainable demand strategy engine · Month-wise decision matrix · Marketing timing & association rules
          </p>
        </div>

        <div className="flex items-center gap-3">
          <div className="glass-card-sm px-3 py-1.5 flex items-center gap-2 text-xs">
            <span className="w-2 h-2 rounded-full bg-emerald-400" />
            <span className="text-slate-300">Target Month: <strong className="text-emerald-300">{summary.selected_month_name || 'Sep'}</strong></span>
          </div>
        </div>
      </div>

      {/* ── Interactive Month Selector Bar (Jan to Dec) ── */}
      <div className="glass-card p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3 border border-indigo-500/30 bg-white">
        <div className="flex items-center gap-2">
          <div className="p-2 rounded-lg bg-indigo-500/20 text-indigo-400 border border-indigo-500/30">
            <Calendar size={18} />
          </div>
          <div>
            <h3 className="text-xs font-bold text-white uppercase tracking-wider">Select Strategy Target Month (Jan – Dec)</h3>
            <p className="text-[11px] text-slate-400">View month-specific seasonal demand, projected units, and tailored strategy rules</p>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-1 bg-slate-950 p-1.5 rounded-xl border border-white/10">
          {MONTHS_LIST.map(m => (
            <button
              key={m.num}
              onClick={() => setSelectedMonth(m.num)}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all cursor-pointer ${
                selectedMonth === m.num
                  ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/40 border border-indigo-400/40 scale-105'
                  : 'text-slate-600 hover:text-indigo-700 hover:bg-slate-200/80'
              }`}
            >
              {m.name}
            </button>
          ))}
        </div>
      </div>

      {/* ── 4-Quadrant Product Opportunity Matrix ── */}
      <div className="glass-card p-5 space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Layers className="text-indigo-400" size={18} />
            <div>
              <h2 className="text-base font-semibold text-white">Product Growth Opportunity Matrix ({summary.selected_month_name})</h2>
              <p className="text-xs text-slate-400">Categorized by 30-day forecasted demand growth and volume for {summary.selected_month_name}</p>
            </div>
          </div>
          <span className="text-[11px] text-slate-400">Click any product to inspect strategy</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Quadrant 1: Priority Products */}
          <div className="glass-card p-4 border border-emerald-500/30 bg-emerald-950/10 space-y-2">
            <div className="flex items-center justify-between border-b border-emerald-500/20 pb-2">
              <h3 className="text-xs font-bold text-emerald-400 flex items-center gap-1.5">
                🟢 Priority Products <span className="text-[10px] font-normal text-slate-400">(High Growth + High Demand)</span>
              </h3>
              <span className="text-[10px] px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 font-bold">{priorityList.length} Items</span>
            </div>
            <div className="space-y-1.5 pt-1">
              {priorityList.map(p => (
                <div
                  key={p.drug_code}
                  onClick={() => setSelectedDrug(p.drug_code)}
                  className={`p-2.5 rounded-lg border transition-all cursor-pointer flex items-center justify-between ${
                    selectedDrug === p.drug_code
                      ? 'bg-emerald-500/20 border-emerald-400 shadow-md'
                      : 'glass-card-sm border-white/5 hover:border-emerald-500/40'
                  }`}
                >
                  <div>
                    <p className="text-xs font-bold text-white flex items-center gap-1">
                      {p.drug_code} <span className="text-[10px] font-normal text-slate-400">({p.drug_name})</span>
                    </p>
                    <p className="text-[10px] text-emerald-300 mt-0.5">
                      {summary.selected_month_name} Forecast: <span className="font-bold">{p.metrics.forecast_30d}</span> units
                    </p>
                  </div>
                  <ChevronRight size={14} className="text-emerald-400" />
                </div>
              ))}
            </div>
          </div>

          {/* Quadrant 2: Emerging Products */}
          <div className="glass-card p-4 border border-cyan-500/30 bg-cyan-950/10 space-y-2">
            <div className="flex items-center justify-between border-b border-cyan-500/20 pb-2">
              <h3 className="text-xs font-bold text-cyan-400 flex items-center gap-1.5">
                🔵 Emerging Products <span className="text-[10px] font-normal text-slate-400">(High Growth + Low Demand)</span>
              </h3>
              <span className="text-[10px] px-2 py-0.5 rounded bg-cyan-500/20 text-cyan-300 font-bold">{emergingList.length} Items</span>
            </div>
            <div className="space-y-1.5 pt-1">
              {emergingList.map(p => (
                <div
                  key={p.drug_code}
                  onClick={() => setSelectedDrug(p.drug_code)}
                  className={`p-2.5 rounded-lg border transition-all cursor-pointer flex items-center justify-between ${
                    selectedDrug === p.drug_code
                      ? 'bg-cyan-500/20 border-cyan-400 shadow-md'
                      : 'glass-card-sm border-white/5 hover:border-cyan-500/40'
                  }`}
                >
                  <div>
                    <p className="text-xs font-bold text-white flex items-center gap-1">
                      {p.drug_code} <span className="text-[10px] font-normal text-slate-400">({p.drug_name})</span>
                    </p>
                    <p className="text-[10px] text-cyan-300 mt-0.5">
                      {summary.selected_month_name} Forecast: <span className="font-bold">{p.metrics.forecast_30d}</span> units
                    </p>
                  </div>
                  <ChevronRight size={14} className="text-cyan-400" />
                </div>
              ))}
            </div>
          </div>

          {/* Quadrant 3: Stable Products */}
          <div className="glass-card p-4 border border-amber-500/30 bg-amber-950/10 space-y-2">
            <div className="flex items-center justify-between border-b border-amber-500/20 pb-2">
              <h3 className="text-xs font-bold text-amber-400 flex items-center gap-1.5">
                🟡 Stable Products <span className="text-[10px] font-normal text-slate-400">(Low Growth + High Demand)</span>
              </h3>
              <span className="text-[10px] px-2 py-0.5 rounded bg-amber-500/20 text-amber-300 font-bold">{stableList.length} Items</span>
            </div>
            <div className="space-y-1.5 pt-1">
              {stableList.map(p => (
                <div
                  key={p.drug_code}
                  onClick={() => setSelectedDrug(p.drug_code)}
                  className={`p-2.5 rounded-lg border transition-all cursor-pointer flex items-center justify-between ${
                    selectedDrug === p.drug_code
                      ? 'bg-amber-500/20 border-amber-400 shadow-md'
                      : 'glass-card-sm border-white/5 hover:border-amber-500/40'
                  }`}
                >
                  <div>
                    <p className="text-xs font-bold text-white flex items-center gap-1">
                      {p.drug_code} <span className="text-[10px] font-normal text-slate-400">({p.drug_name})</span>
                    </p>
                    <p className="text-[10px] text-amber-300 mt-0.5">
                      {summary.selected_month_name} Forecast: <span className="font-bold">{p.metrics.forecast_30d}</span> units
                    </p>
                  </div>
                  <ChevronRight size={14} className="text-amber-400" />
                </div>
              ))}
            </div>
          </div>

          {/* Quadrant 4: Low Priority Products */}
          <div className="glass-card p-4 border border-red-500/30 bg-red-950/10 space-y-2">
            <div className="flex items-center justify-between border-b border-red-500/20 pb-2">
              <h3 className="text-xs font-bold text-red-400 flex items-center gap-1.5">
                🔴 Low Priority Products <span className="text-[10px] font-normal text-slate-400">(Low Growth + Low Demand)</span>
              </h3>
              <span className="text-[10px] px-2 py-0.5 rounded bg-red-500/20 text-red-300 font-bold">{lowList.length} Items</span>
            </div>
            <div className="space-y-1.5 pt-1">
              {lowList.map(p => (
                <div
                  key={p.drug_code}
                  onClick={() => setSelectedDrug(p.drug_code)}
                  className={`p-2.5 rounded-lg border transition-all cursor-pointer flex items-center justify-between ${
                    selectedDrug === p.drug_code
                      ? 'bg-red-500/20 border-red-400 shadow-md'
                      : 'glass-card-sm border-white/5 hover:border-red-500/40'
                  }`}
                >
                  <div>
                    <p className="text-xs font-bold text-white flex items-center gap-1">
                      {p.drug_code} <span className="text-[10px] font-normal text-slate-400">({p.drug_name})</span>
                    </p>
                    <p className="text-[10px] text-red-300 mt-0.5">
                      {summary.selected_month_name} Forecast: <span className="font-bold">{p.metrics.forecast_30d}</span> units
                    </p>
                  </div>
                  <ChevronRight size={14} className="text-red-400" />
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* ── Product Strategy Inspector ── */}
      {selectedProduct && (
        <div className="glass-card p-5 space-y-4 border border-indigo-500/30">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-white/10 pb-3">
            <div>
              <div className="flex items-center gap-2">
                <span className="text-lg font-bold text-white font-mono">{selectedProduct.drug_code}</span>
                <span className="text-xs text-slate-400">({selectedProduct.drug_name})</span>
                <span className={`text-xs px-2.5 py-0.5 rounded-full font-bold border ${QUADRANT_COLORS[selectedProduct.quadrant].badge}`}>
                  {selectedProduct.quadrant_label}
                </span>
                <span className="text-xs px-2.5 py-0.5 rounded-full font-bold bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                  Target: {summary.selected_month_name}
                </span>
              </div>
              <p className="text-xs text-slate-400 mt-1">
                Historical 30d Avg: <span className="font-mono text-slate-200">{selectedProduct.metrics.historical_30d_avg}</span> | {summary.selected_month_name} Forecast: <span className="font-mono text-indigo-300 font-bold">{selectedProduct.metrics.forecast_30d}</span> units
              </p>
            </div>

            {/* Category Selector */}
            <select
              value={selectedDrug}
              onChange={e => setSelectedDrug(e.target.value)}
              className="glass-card-sm px-3 py-1.5 text-xs text-slate-900 bg-white border border-slate-300 cursor-pointer self-start"
            >
              {DRUGS.map(d => (
                <option key={d} value={d} >{d} - {DRUG_FULL_NAMES[d]}</option>
              ))}
            </select>
          </div>

          {/* Strategy Cards Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* 1. Sales Strategy Card */}
            <div className="glass-card p-4 border border-indigo-500/20 space-y-2">
              <div className="flex items-center justify-between">
                <h4 className="text-xs font-bold text-indigo-300 flex items-center gap-1.5">
                  <ShoppingBag size={14} /> Sales Strategy ({summary.selected_month_name})
                </h4>
                <span className="text-[10px] px-2 py-0.5 rounded bg-indigo-500/20 text-indigo-300 font-semibold">
                  {selectedProduct.sales_strategy.opportunity_level}
                </span>
              </div>
              <p className="text-xs text-slate-200 leading-relaxed font-medium mt-1">
                {selectedProduct.sales_strategy.action}
              </p>
              <div className="pt-2 border-t border-white/5 text-[11px] text-slate-400 space-y-1">
                <p>Stock Focus: <span className="text-indigo-300 font-semibold">{selectedProduct.sales_strategy.stock_focus}</span></p>
                <p>Urgency: <span className="text-amber-300 font-semibold">{selectedProduct.sales_strategy.replenishment_urgency}</span></p>
              </div>
            </div>

            {/* 2. Marketing Strategy Card */}
            <div className="glass-card p-4 border border-cyan-500/20 space-y-2">
              <div className="flex items-center justify-between">
                <h4 className="text-xs font-bold text-cyan-300 flex items-center gap-1.5">
                  <Megaphone size={14} /> Marketing Strategy ({summary.selected_month_name})
                </h4>
                <span className="text-[10px] px-2 py-0.5 rounded bg-cyan-500/20 text-cyan-300 font-semibold">
                  Intensity: {selectedProduct.marketing_strategy.intensity}
                </span>
              </div>
              <p className="text-xs font-semibold text-cyan-400">
                {selectedProduct.marketing_strategy.focus}
              </p>
              <p className="text-xs text-slate-300 leading-relaxed">
                {selectedProduct.marketing_strategy.timing_recommendation}
              </p>
              <div className="pt-2 border-t border-white/5 text-[11px] text-slate-400">
                Action: <span className="text-cyan-300">{selectedProduct.marketing_strategy.action}</span>
              </div>
            </div>
          </div>

          {/* Rationale Explanation */}
          <div className="glass-card-sm p-3 border-l-2 border-indigo-400 bg-indigo-950/20 text-xs text-slate-300 flex items-start gap-2">
            <Sparkles size={16} className="text-indigo-400 shrink-0 mt-0.5" />
            <div>
              <p className="font-semibold text-indigo-300 mb-0.5">Deterministic System Rationale ({summary.selected_month_name})</p>
              <p className="text-slate-300">{selectedProduct.rationale}</p>
            </div>
          </div>
        </div>
      )}

      {/* ── Cross-Selling & Product Association Matrix ── */}
      <div className="glass-card p-5 space-y-4">
        <div className="flex items-center gap-2">
          <Repeat className="text-purple-400" size={18} />
          <div>
            <h3 className="text-sm font-semibold text-white">Cross-Selling & Product Association Rules</h3>
            <p className="text-[11px] text-slate-400">Co-purchasing affinity analysis derived from multi-category transaction data</p>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-white/10 text-slate-400 text-left">
                <th className="pb-2">Primary Category (A)</th>
                <th className="pb-2">Co-Purchased Category (B)</th>
                <th className="pb-2 text-left pl-4">Recommended Cross-Sell Directive</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              {association_rules.map((rule, idx) => (
                <tr key={idx} className="hover:bg-white/5 transition-colors">
                  <td className="py-3 font-mono font-bold text-indigo-300">
                    {rule.antecedent} <span className="text-[10px] font-normal text-slate-400 block">{rule.antecedent_name}</span>
                  </td>
                  <td className="py-3 font-mono font-bold text-purple-300">
                    + {rule.consequent} <span className="text-[10px] font-normal text-slate-400 block">{rule.consequent_name}</span>
                  </td>
                  <td className="py-3 pl-4 text-slate-300 leading-snug">{rule.recommendation}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

function LoadingState() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] space-y-4">
      <div className="w-12 h-12 rounded-full border-2 border-indigo-500 border-t-transparent animate-spin" />
      <p className="text-slate-400 text-xs animate-pulse font-medium">Evaluating strategy rules and opportunity matrices…</p>
    </div>
  )
}

function ErrorState({ onRetry }: { onRetry: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] text-center">
      <div className="glass-card p-6 max-w-md space-y-4">
        <AlertCircle size={36} className="text-amber-400 mx-auto" />
        <h2 className="text-white font-semibold text-base">Strategy Data Unavailable</h2>
        <p className="text-slate-400 text-xs">
          Could not fetch strategy recommendations from backend FastAPI server. Please check backend connection.
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
