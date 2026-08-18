import React, { useState, useEffect, useRef } from 'react'
import api from '@/api/client'
import {
  Play,
  Pause,
  SkipForward,
  RotateCcw,
  AlertTriangle,
  CheckCircle2,
  Clock,
  TrendingUp,
  PackageCheck,
  Zap,
  Activity,
  Calendar,
  Layers,
  FileText,
  Sliders,
  Check,
  X,
  Edit2,
  RefreshCw,
  Award,
} from 'lucide-react'
import {
  LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Cell,
} from 'recharts'

const API_BASE = 'http://localhost:8000/api/simulation'


export function HackathonDashboard() {
  const [state, setState] = useState<any>(null)
  const [loading, setLoading] = useState<boolean>(true)
  const [activeTab, setActiveTab] = useState<'simulation' | 'monthly' | 'validation' | 'baselines' | 'audit'>('simulation')
  const [validationData, setValidationData] = useState<any>(null)
  const [transactions, setTransactions] = useState<any[]>([])
  const [monthlyRecords, setMonthlyRecords] = useState<any[]>([])

  // Modal / Drawer state for approving replenishment
  const [selectedDrug, setSelectedDrug] = useState<any>(null)
  const [customQty, setCustomQty] = useState<string>('')
  const [customLeadTime, setCustomLeadTime] = useState<number>(4)
  const [isEditingQty, setIsEditingQty] = useState<boolean>(false)

  // Simulation auto-play timer ref
  const timerRef = useRef<any>(null)

  const fetchState = async () => {
    try {
      const res = await api.get('/simulation/state')
      if (res.data) {
        const data = res.data
        setState(data)
      }
    } catch (err) {
      console.error('Failed to fetch state:', err)
    } finally {
      setLoading(false)
    }
  }

  const fetchValidation = async () => {
    try {
      const res = await api.get('/simulation/validation')
      if (res.data) {
        const data = res.data
        setValidationData(data)
      }
    } catch (err) {
      console.error('Failed to fetch validation:', err)
    }
  }

  const fetchTransactions = async () => {
    try {
      const res = await api.get('/simulation/transactions?limit=50')
      if (res.data) {
        const data = res.data
        setTransactions(data)
      }
    } catch (err) {
      console.error('Failed to fetch transactions:', err)
    }
  }

  const fetchMonthlyRecords = async () => {
    try {
      const res = await api.get('/simulation/monthly_records')
      if (res.data) {
        const data = res.data
        setMonthlyRecords(data)
      }
    } catch (err) {
      console.error('Failed to fetch monthly records:', err)
    }
  }

  useEffect(() => {
    fetchState()
    fetchValidation()
    fetchTransactions()
    fetchMonthlyRecords()
  }, [])


  // Auto-step simulation loop when status === 'running'
  useEffect(() => {
    if (state?.status === 'running') {
      const speedMs =
        state.speed === '0.25x' || state.speed === '0.25' ? 1000 :
        state.speed === '0.50x' || state.speed === '0.50' ? 600 :
        state.speed === '0.75x' || state.speed === '0.75' ? 400 :
        300 // Fast 1x default pace: 300ms per simulation day
      timerRef.current = setInterval(async () => {
        try {
          const res = await api.post('/simulation/step')
          if (res.data) {
            const data = res.data
            setState(data)
          }
        } catch (err) {
          console.error('Step error:', err)
        }
      }, speedMs)
    } else {
      if (timerRef.current) clearInterval(timerRef.current)
    }

    return () => {
      if (timerRef.current) clearInterval(timerRef.current)
    }
  }, [state?.status, state?.speed])

  const handleStep = async () => {
    try {
      const res = await api.post('/simulation/step')
      if (res.data) {
        const data = res.data
        setState(data)
        fetchTransactions()
      }
    } catch (err) {
      console.error('Step error:', err)
    }
  }

  const handleStepMonth = async () => {
    try {
      const res = await api.post('/simulation/step_month')
      if (res.data) {
        const data = res.data
        setState(data)
        fetchTransactions()
        fetchMonthlyRecords()
      }
    } catch (err) {
      console.error('Step month error:', err)
    }
  }

  const handleControl = async (status?: string, speed?: string) => {
    try {
      const res = await api.post('/simulation/control', { status, speed })
      if (res.data) {
        const data = res.data
        setState(data)
      }
    } catch (err) {
      console.error('Control error:', err)
    }
  }

  const handleReset = async () => {
    try {
      const res = await api.post('/simulation/reset')
      if (res.data) {
        const data = res.data
        setState(data)
        fetchTransactions()
        fetchMonthlyRecords()
      }
    } catch (err) {
      console.error('Reset error:', err)
    }
  }

  const handleOrderAction = async (
    drugId: string,
    action: 'approve' | 'edit' | 'reject',
    qty?: number,
    leadTimeDays?: number
  ) => {
    try {
      const res = await api.post('/simulation/order/action', { drug_id: drugId, action, quantity: qty, lead_time_days: leadTimeDays, user_name: 'Pharmacy Member' })
      if (res.data) {
        const data = res.data
        setState(data)
        setSelectedDrug(null)
        setIsEditingQty(false)
        fetchTransactions()
      }
    } catch (err) {
      console.error('Order action error:', err)
    }
  }

  const handleLeadTimeChange = async (drugId: string, leadTimeDays: number) => {
    try {
      const res = await api.post('/simulation/lead_time', { drug_id: drugId, lead_time_days: leadTimeDays })
      if (res.data) {
        const data = res.data
        setState(data)
      }
    } catch (err) {
      console.error('Lead time update error:', err)
    }
  }

  const handleGlobalLeadTimeChange = async (leadTimeDays: number) => {
    try {
      const res = await api.post('/simulation/lead_time_all', { lead_time_days: leadTimeDays })
      if (res.data) {
        const data = res.data
        setState(data)
      }
    } catch (err) {
      console.error('Global lead time update error:', err)
    }
  }

  const handleBaselineAction = async (drugId: string, action: 'accept' | 'edit' | 'reject', newBaseline?: number) => {
    try {
      const res = await api.post('/simulation/baseline/action', { drug_id: drugId, action, new_baseline: newBaseline, reason: 'Sustained demand increase', user_name: 'Pharmacy Member' })
      if (res.data) {
        const data = res.data
        setState(data)
        fetchTransactions()
      }
    } catch (err) {
      console.error('Baseline action error:', err)
    }
  }

  if (loading || !state) {
    return (
      <div className="flex h-screen items-center justify-center bg-[#f3f5fa] text-slate-900">
        <div className="flex items-center gap-3">
          <RefreshCw className="animate-spin text-indigo-600" size={24} />
          <span className="font-semibold">Loading Pharmacy Simulation Engine...</span>
        </div>
      </div>
    )
  }

  const { current_date, status, speed, summary, drugs } = state

  // Format date for presentation
  const dateObj = new Date(current_date)
  const formattedDate = dateObj.toLocaleDateString('en-US', {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  })

  // Priority drugs requiring member action
  const alertDrugs = drugs.filter((d: any) =>
    ['STOCKOUT_RISK', 'EMERGENCY_REPLENISHMENT', 'OUT_OF_STOCK', 'REPLENISHMENT_RECOMMENDED'].includes(d.risk_level)
  )

  return (
    <div className="min-h-screen bg-[#f3f5fa] text-slate-800 p-6 space-y-6">

      {/* Header Bar */}
      <header className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 p-5 rounded-2xl bg-white border border-slate-200 shadow-sm">

        <div>
          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-500 font-mono">2019 Day-by-Day Simulation</span>
          </div>
          <h1 className="text-2xl font-black tracking-tight text-slate-900 mt-1">
            Forecast-Driven Pharmacy Demand & Inventory System
          </h1>
        </div>

        {/* Live Simulation Clock & Controls */}
        <div className="flex flex-wrap items-center gap-3 bg-slate-50 p-2.5 rounded-2xl border border-slate-200">
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-indigo-50 border border-indigo-200 text-indigo-800">
            <Calendar size={18} className="text-indigo-600" />
            <span className="font-bold font-mono text-sm tracking-wide">{formattedDate}</span>
          </div>

          <div className="flex items-center gap-1.5">
            {status === 'running' ? (
              <button
                onClick={() => handleControl('paused')}
                className="flex items-center gap-1.5 px-4 py-1.5 rounded-full bg-amber-500 text-white hover:bg-amber-600 transition text-xs font-bold shadow-sm cursor-pointer"
              >
                <Pause size={14} /> Pause
              </button>
            ) : (
              <button
                onClick={() => handleControl('running')}
                className="flex items-center gap-1.5 px-4 py-1.5 rounded-full bg-emerald-600 text-white hover:bg-emerald-700 transition text-xs font-bold shadow-sm cursor-pointer"
              >
                <Play size={14} /> Start
              </button>
            )}

            <button
              onClick={handleStep}
              className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-full bg-white text-slate-700 hover:bg-slate-100 transition text-xs font-bold border border-slate-300 shadow-sm cursor-pointer"
            >
              <SkipForward size={14} /> Next Day
            </button>

            <button
              onClick={handleStepMonth}
              className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-full bg-indigo-600 text-white hover:bg-indigo-700 transition text-xs font-bold shadow-sm cursor-pointer"
              title="Run simulation to the end of current month"
            >
              <Calendar size={14} /> Next Month
            </button>

            <button
              onClick={handleReset}
              className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-full bg-slate-100 text-slate-600 hover:text-slate-900 hover:bg-slate-200 transition text-xs font-bold border border-slate-300 shadow-sm cursor-pointer"
              title="Reset to 2019-01-01"
            >
              <RotateCcw size={14} /> Restart
            </button>
          </div>

          {/* Speed Selector */}
          <div className="flex items-center bg-white rounded-full p-1 border border-slate-200 text-xs shadow-sm">
            {['0.25x', '0.50x', '0.75x', '1x'].map((spd) => (
              <button
                key={spd}
                onClick={() => handleControl(undefined, spd)}
                className={`px-2.5 py-1 rounded-full font-mono font-bold transition cursor-pointer ${
                  speed === spd ? 'bg-indigo-600 text-white shadow-sm' : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                {spd}
              </button>
            ))}
          </div>

          {/* Global Resupply Lead Time Selector (One-click for ALL drugs) */}
          <div className="flex items-center gap-1 bg-white rounded-full p-1 border border-slate-200 text-xs shadow-sm">
            <span className="text-[11px] text-slate-500 font-semibold px-2">All Resupply:</span>
            {[1, 2, 3, 4, 5, 6, 7].map((days) => {
              const isSelected = drugs.every((d: any) => (d.lead_time_days || 4) === days)
              return (
                <button
                  key={days}
                  onClick={() => handleGlobalLeadTimeChange(days)}
                  className={`px-2.5 py-1 rounded-full font-mono font-bold transition cursor-pointer ${
                    isSelected
                      ? 'bg-emerald-600 text-white shadow-sm'
                      : 'bg-slate-50 text-slate-600 hover:text-slate-900 border border-slate-200'
                  }`}
                  title={`Set ${days} Day${days > 1 ? 's' : ''} resupply lead time for ALL drugs`}
                >
                  {days}d
                </button>
              )
            })}
          </div>
        </div>
      </header>

      {/* Auto-Paused Stockout Risk Banner */}
      {state?.pause_reason && (
        <div className="bg-rose-500/10 border border-rose-500/30 rounded-xl p-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-rose-500/20 text-rose-400">
              <AlertTriangle size={20} />
            </div>
            <div>
              <p className="font-bold text-rose-300 text-sm">Simulation Paused — Action Required</p>
              <p className="text-xs text-rose-200/80 mt-0.5">{state.pause_reason}</p>
            </div>
          </div>
          <span className="text-xs font-mono font-bold px-2.5 py-1 rounded bg-rose-500/20 text-rose-300 border border-rose-500/40 animate-pulse">
            PAUSED
          </span>
        </div>
      )}

      {/* Summary KPI Strip */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        <div className="p-4 rounded-xl bg-white border border-slate-200 shadow-sm">
          <div className="flex items-center justify-between text-xs text-slate-500 font-medium">
            <span>Healthy</span>
            <CheckCircle2 size={16} className="text-emerald-400" />
          </div>
          <p className="text-2xl font-extrabold text-emerald-400 mt-2">{summary.HEALTHY || 0}</p>
        </div>

        <div className="p-4 rounded-xl bg-white border border-slate-200 shadow-sm">
          <div className="flex items-center justify-between text-xs text-slate-500 font-medium">
            <span>Watch (≥60%)</span>
            <Activity size={16} className="text-yellow-400" />
          </div>
          <p className="text-2xl font-extrabold text-yellow-400 mt-2">{summary.WATCH || 0}</p>
        </div>

        <div className="p-4 rounded-xl bg-white border border-slate-200 shadow-sm">
          <div className="flex items-center justify-between text-xs text-slate-500 font-medium">
            <span>Reorder (≥70%)</span>
            <Clock size={16} className="text-orange-400" />
          </div>
          <p className="text-2xl font-extrabold text-orange-400 mt-2">{summary.REPLENISHMENT_RECOMMENDED || 0}</p>
        </div>

        <div className="p-4 rounded-xl bg-white border border-slate-200 shadow-sm">
          <div className="flex items-center justify-between text-xs text-slate-500 font-medium">
            <span>Stockout Risk</span>
            <AlertTriangle size={16} className="text-red-400" />
          </div>
          <p className="text-2xl font-extrabold text-red-400 mt-2">{summary.STOCKOUT_RISK || 0}</p>
        </div>

        <div className="p-4 rounded-xl bg-white border border-slate-200 shadow-sm">
          <div className="flex items-center justify-between text-xs text-slate-500 font-medium">
            <span>Emergency</span>
            <Zap size={16} className="text-rose-500" />
          </div>
          <p className="text-2xl font-extrabold text-rose-500 mt-2">{summary.EMERGENCY_REPLENISHMENT || 0}</p>
        </div>

        <div className="p-4 rounded-xl bg-white border border-slate-200 shadow-sm">
          <div className="flex items-center justify-between text-xs text-slate-500 font-medium">
            <span>Out of Stock</span>
            <PackageCheck size={16} className="text-rose-600" />
          </div>
          <p className="text-2xl font-extrabold text-rose-600 mt-2">{summary.OUT_OF_STOCK || 0}</p>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="flex items-center border-b border-slate-200 gap-6">
        <button
          onClick={() => setActiveTab('simulation')}
          className={`flex items-center gap-2 pb-3 font-semibold text-sm transition border-b-2 ${
            activeTab === 'simulation'
              ? 'border-indigo-600 text-indigo-600'
              : 'border-transparent text-slate-500 hover:text-slate-900'
          }`}
        >
          <Layers size={16} /> Live Simulation
        </button>

        <button
          onClick={() => setActiveTab('baselines')}
          className={`flex items-center gap-2 pb-3 font-semibold text-sm transition border-b-2 ${
            activeTab === 'baselines'
              ? 'border-indigo-600 text-indigo-600'
              : 'border-transparent text-slate-500 hover:text-slate-900'
          }`}
        >
          <Sliders size={16} /> Baseline Management
        </button>
      </div>

      {/* TAB 1: Live Simulation Dashboard */}
      {activeTab === 'simulation' && (
        <div className="space-y-6">
          {/* Priority Alerts Drawer / Banner */}
          {alertDrugs.length > 0 && (
            <div className="p-5 rounded-2xl bg-amber-50 border border-amber-500/40 space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-amber-400">
                  <AlertTriangle size={20} />
                  <h3 className="font-bold text-base">Pharmacy Member Review Required ({alertDrugs.length} Drugs)</h3>
                </div>
                <span className="text-xs text-amber-300 font-mono">Human-in-the-loop Decision Support</span>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                {alertDrugs.map((d: any) => (
                  <div key={d.drug_id} className="p-4 rounded-xl bg-white border border-slate-200 space-y-3">
                    <div className="flex items-center justify-between">
                      <span className="font-black text-lg text-slate-900 font-mono">{d.drug_code}</span>
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] font-extrabold uppercase tracking-wider ${
                          d.risk_level === 'STOCKOUT_RISK' || d.risk_level === 'EMERGENCY_REPLENISHMENT'
                            ? 'bg-rose-500/20 text-rose-400 border border-rose-500/30'
                            : 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
                        }`}
                      >
                        {d.risk_level.replace('_', ' ')}
                      </span>
                    </div>

                    <div className="text-xs text-slate-700 space-y-1 font-mono">
                      <div className="flex justify-between"><span>Current Stock:</span> <strong className="text-slate-900">{d.current_stock}</strong></div>
                      <div className="flex justify-between"><span>Baseline Stock:</span> <span>{d.baseline_stock}</span></div>
                      <div className="flex justify-between"><span>Consumed:</span> <span className="text-amber-400 font-bold">{d.consumed_pct}%</span></div>
                      <div className="flex justify-between"><span>Forecast 7 Days:</span> <span className="text-indigo-600 font-bold">{d.forecast_7day}</span></div>
                      <div className="flex justify-between"><span>Safety Stock:</span> <span>{d.safety_stock}</span></div>
                      <div className="flex justify-between border-t border-slate-200 pt-1 font-bold text-slate-900">
                        <span>Recommended Order:</span> <span className="text-emerald-400">{d.recommended_order} units</span>
                      </div>
                    </div>

                    {d.pending_order ? (
                      <div className="p-2 rounded bg-indigo-950/60 border border-indigo-800/50 text-[11px] text-indigo-300 flex items-center justify-between">
                        <span>Shipment Pending ({d.pending_order.quantity} units)</span>
                        <span className="font-mono text-indigo-600">Arrives: {d.pending_order.expected_arrival}</span>
                      </div>
                    ) : (
                      <div className="flex items-center gap-2 pt-1">
                        <button
                          onClick={() => handleOrderAction(d.drug_id, 'approve')}
                          className="flex-1 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-slate-900 font-bold text-xs transition"
                        >
                          Approve
                        </button>
                        <button
                          onClick={() => {
                            setSelectedDrug(d)
                            setCustomQty(d.recommended_order.toString())
                            setCustomLeadTime(d.lead_time_days || 4)
                            setIsEditingQty(true)
                          }}
                          className="flex-1 py-1.5 px-3 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 font-bold text-xs transition border border-slate-700 text-center"
                        >
                          Edit
                        </button>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Main Drugs Inventory Table */}
          <div className="rounded-2xl bg-white border border-slate-200 overflow-hidden shadow-sm">
            <div className="p-4 border-b border-slate-200 flex items-center justify-between">
              <div>
                <h3 className="font-bold text-lg text-slate-900">All Pharmacy Drugs Inventory State</h3>
                <p className="text-xs text-slate-500">Daily sales consumption & 7-day forecast stockout prediction</p>
              </div>
              <span className="text-xs font-mono text-indigo-600">8 Medicines Monitored</span>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs text-slate-700">
                <thead className="bg-slate-50 uppercase text-[10px] text-slate-500 font-bold tracking-wider font-semibold border-b border-slate-200">
                  <tr>
                    <th className="p-3.5">Drug Code</th>
                    <th className="p-3.5">Category</th>
                    <th className="p-3.5">Today Sales</th>
                    <th className="p-3.5">Current Stock</th>
                    <th className="p-3.5">Baseline</th>
                    <th className="p-3.5">Consumed</th>
                    <th className="p-3.5">Forecast 7-Day</th>
                    <th className="p-3.5">Resupply Days</th>
                    <th className="p-3.5">Projected Stock</th>
                    <th className="p-3.5">Risk State</th>
                    <th className="p-3.5">Reorder Qty</th>
                    <th className="p-3.5 text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 font-mono">
                  {drugs.map((d: any) => {
                    const consumedColor =
                      d.consumed_pct >= 70 ? 'text-orange-400 font-bold' : d.consumed_pct >= 60 ? 'text-yellow-400' : 'text-slate-700'
                    return (
                      <tr key={d.drug_id} className="hover:bg-slate-50/80 transition">
                        <td className="p-3.5 font-extrabold text-slate-900 font-sans">
                          {d.drug_code}
                          <p className="text-[10px] text-slate-500 font-normal truncate max-w-[120px]">{d.drug_name}</p>
                        </td>
                        <td className="p-3.5 font-sans text-slate-500">{d.category}</td>
                        <td className="p-3.5 text-indigo-600 font-bold">{d.today_sales}</td>
                        <td className="p-3.5 font-bold text-slate-900">{Math.round(Number(d.current_stock) * 10) / 10}</td>
                        <td className="p-3.5 text-slate-500">{d.baseline_stock}</td>
                        <td className="p-3.5">
                          <span className={consumedColor}>{d.consumed_pct}%</span>
                          <div className="w-16 h-1.5 bg-slate-800 rounded-full mt-1 overflow-hidden">
                            <div
                              className={`h-full ${
                                d.consumed_pct >= 70 ? 'bg-orange-500' : d.consumed_pct >= 60 ? 'bg-yellow-500' : 'bg-emerald-500'
                              }`}
                              style={{ width: `${Math.min(100, d.consumed_pct)}%` }}
                            />
                          </div>
                        </td>
                        <td className="p-3.5 text-indigo-300">{d.forecast_7day}</td>
                        <td className="p-3.5 font-sans">
                          <select
                            value={d.lead_time_days || 4}
                            onChange={(e) => handleLeadTimeChange(d.drug_id, Number(e.target.value))}
                            className="bg-white border border-slate-300 text-indigo-700 shadow-sm text-xs rounded px-1.5 py-0.5 font-mono focus:outline-none focus:border-indigo-500 cursor-pointer"
                            title="Set Resupply Lead Time Days"
                          >
                            <option value={1}>⚡ 1 Day</option>
                            <option value={2}>📦 2 Days</option>
                            <option value={3}>📦 3 Days</option>
                            <option value={4}>🚚 4 Days</option>
                            <option value={5}>🚚 5 Days</option>
                            <option value={6}>🚚 6 Days</option>
                            <option value={7}>🗓️ 7 Days</option>
                          </select>
                        </td>
                        <td className="p-3.5">
                          <span className={d.projected_stock < d.safety_stock ? 'text-rose-600 font-bold' : 'text-slate-700'}>
                            {d.projected_stock}
                          </span>
                        </td>
                        <td className="p-3.5">
                          <span
                            className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold font-sans ${
                              d.risk_level === 'HEALTHY'
                                ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                                : d.risk_level === 'WATCH'
                                ? 'bg-amber-50 text-amber-700 border border-amber-200'
                                : d.risk_level === 'REPLENISHMENT_RECOMMENDED'
                                ? 'bg-orange-50 text-orange-700 border border-orange-200'
                                : 'bg-rose-50 text-rose-700 border border-rose-200'
                            }`}
                          >
                            {d.risk_level}
                          </span>
                        </td>
                        <td className="p-3.5 font-bold text-emerald-600">
                          {d.recommended_order > 0 ? `${d.recommended_order} units` : '—'}
                        </td>
                        <td className="p-3.5 text-right font-sans">
                          {d.pending_order ? (
                            <span className="text-[10px] text-indigo-700 bg-indigo-50 px-2.5 py-1 rounded-full border border-indigo-200 font-bold">
                              Incoming ({d.pending_order.quantity})
                            </span>
                          ) : d.recommended_order > 0 ? (
                            <button
                              onClick={() => handleOrderAction(d.drug_id, 'approve')}
                              className="px-3 py-1 rounded-full bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs transition shadow-sm cursor-pointer"
                            >
                              Reorder
                            </button>
                          ) : (
                            <span className="text-slate-400 text-[11px]">Healthy</span>
                          )}
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}



      {/* TAB 2: Baseline Management */}
      {activeTab === 'baselines' && (
        <div className="p-6 rounded-2xl bg-white border border-slate-200 space-y-4 shadow-sm">
          <div>
            <h3 className="text-xl font-extrabold text-slate-900">Baseline Stock Management</h3>
            <p className="text-xs text-slate-500">
              Baseline stock represents expected normal operational stock. Baseline changes occur on sustained forecast shifts.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {drugs.map((d: any) => (
              <div key={d.drug_id} className="p-4 rounded-xl bg-slate-50 border border-slate-200 flex items-center justify-between">
                <div>
                  <h4 className="font-extrabold text-slate-900 text-base font-mono">{d.drug_code}</h4>
                  <p className="text-xs text-slate-500">{d.drug_name}</p>
                  <p className="text-xs text-slate-700 font-mono mt-2">
                    Current Baseline: <strong className="text-slate-900">{d.baseline_stock} units</strong>
                  </p>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    onClick={() => handleBaselineAction(d.drug_id, 'accept', Math.round(d.baseline_stock * 1.1))}
                    className="px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-slate-900 font-bold text-xs transition"
                  >
                    +10% Baseline
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Edit Quantity & Resupply Lead Time Modal */}
      {isEditingQty && selectedDrug && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div className="bg-white border border-slate-200 rounded-2xl p-6 max-w-md w-full space-y-4 shadow-2xl">
            <h3 className="text-lg font-bold text-slate-900">Configure Replenishment Order ({selectedDrug.drug_code})</h3>
            <p className="text-xs text-slate-500">
              System recommended order: <strong className="text-emerald-400">{selectedDrug.recommended_order} units</strong>
            </p>

            <div className="space-y-3">
              <div className="space-y-1">
                <label className="text-xs text-slate-700 font-semibold">Custom Order Quantity (Units)</label>
                <input
                  type="number"
                  value={customQty}
                  onChange={(e) => setCustomQty(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl bg-[#f3f5fa] border border-slate-700 text-slate-900 font-mono text-sm focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div className="space-y-1">
                <label className="text-xs text-slate-700 font-semibold">Resupply Lead Time (Supplier Delivery Days)</label>
                <select
                  value={customLeadTime}
                  onChange={(e) => setCustomLeadTime(Number(e.target.value))}
                  className="w-full px-3 py-2 rounded-xl bg-white border border-slate-300 text-indigo-700 shadow-sm font-mono text-sm focus:outline-none focus:border-indigo-500"
                >
                  <option value={1}>⚡ 1 Day (Express Delivery)</option>
                  <option value={2}>📦 2 Days (Priority Delivery)</option>
                  <option value={3}>📦 3 Days (Fast Courier)</option>
                  <option value={4}>🚚 4 Days (Standard Supplier)</option>
                  <option value={5}>🚚 5 Days (Extended Supply)</option>
                  <option value={6}>🚚 6 Days (Weekly Supply)</option>
                  <option value={7}>🗓️ 7 Days (Weekly Shipment)</option>
                </select>
              </div>
            </div>

            <div className="flex items-center gap-3 pt-3">
              <button
                onClick={() =>
                  handleOrderAction(
                    selectedDrug.drug_id,
                    'edit',
                    parseFloat(customQty),
                    customLeadTime
                  )
                }
                className="flex-1 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-slate-900 font-bold text-xs transition shadow-lg shadow-emerald-950"
              >
                Confirm & Approve Order
              </button>
              <button
                onClick={() => setIsEditingQty(false)}
                className="py-2 px-4 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-700 font-bold text-xs transition"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
