// src/pages/LogsPage.tsx
import { useState, useEffect, useCallback } from "react";
import api from "@/api/client";
import {
  FileText, RefreshCw, Search, Filter, ChevronDown,
  CheckCircle, XCircle, AlertTriangle, Info,
  LogIn, LogOut, Zap, Shield, Activity, Terminal,
  Key, Mail,
} from "lucide-react";

interface LogEntry {
  id?: number;
  event_type: string;
  username: string;
  user_role: string;
  message: string;
  detail?: string;
  status: string;
  ip_address?: string;
  user_agent?: string;
  created_at: string;
}

interface LogSummary {
  [event_type: string]: { SUCCESS: number; ERROR: number; WARNING: number; INFO: number; total: number };
}

const EVENT_TYPES = [
  "ALL", "LOGIN", "LOGOUT",
  "API_CALL", "API_ERROR",
  "PAGE_VIEW",
  "PASSWORD_CHANGED",
  "STOCK_UPDATED", "BASELINE_STOCK_CHANGED",
  "ADMIN_ACTION", "EMAIL_SENT",
  "SIM_ACTION", "ERROR", "INFO",
];
const STATUSES = ["ALL", "SUCCESS", "ERROR", "WARNING", "INFO"];

const EVENT_ICONS: Record<string, any> = {
  LOGIN:                  LogIn,
  LOGOUT:                 LogOut,
  API_CALL:               Zap,
  API_ERROR:              XCircle,
  PAGE_VIEW:              FileText,
  PASSWORD_CHANGED:       Key,
  STOCK_UPDATED:          Activity,
  BASELINE_STOCK_CHANGED: Activity,
  ADMIN_ACTION:           Shield,
  EMAIL_SENT:             Mail,
  SIM_ACTION:             Activity,
  ERROR:                  XCircle,
  INFO:                   Info,
};

const STATUS_COLORS: Record<string, string> = {
  SUCCESS: "text-emerald-400 bg-emerald-500/10 border-emerald-500/30",
  ERROR:   "text-red-400 bg-red-500/10 border-red-500/30",
  WARNING: "text-amber-400 bg-amber-500/10 border-amber-500/30",
  INFO:    "text-sky-400 bg-sky-500/10 border-sky-500/30",
};

const STATUS_ICONS: Record<string, any> = {
  SUCCESS: CheckCircle,
  ERROR:   XCircle,
  WARNING: AlertTriangle,
  INFO:    Info,
};

const EVENT_TYPE_COLORS: Record<string, string> = {
  LOGIN:                  "text-emerald-300 bg-emerald-500/10",
  LOGOUT:                 "text-slate-400 bg-slate-500/10",
  API_CALL:               "text-indigo-300 bg-indigo-500/10",
  API_ERROR:              "text-red-300 bg-red-500/10",
  PAGE_VIEW:              "text-sky-300 bg-sky-500/10",
  PASSWORD_CHANGED:       "text-amber-300 bg-amber-500/10",
  STOCK_UPDATED:          "text-cyan-300 bg-cyan-500/10",
  BASELINE_STOCK_CHANGED: "text-violet-300 bg-violet-500/10",
  ADMIN_ACTION:           "text-amber-300 bg-amber-500/10",
  EMAIL_SENT:             "text-teal-300 bg-teal-500/10",
  SIM_ACTION:             "text-purple-300 bg-purple-500/10",
  ERROR:                  "text-red-300 bg-red-500/10",
  INFO:                   "text-slate-300 bg-slate-500/10",
};

function formatTime(ts: string) {
  try {
    const d = new Date(ts);
    return d.toLocaleString("en-IN", {
      day: "2-digit", month: "short", year: "numeric",
      hour: "2-digit", minute: "2-digit", second: "2-digit",
      hour12: true,
    });
  } catch { return ts; }
}

export function LogsPage() {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [summary, setSummary] = useState<LogSummary>({});
  const [totalEvents, setTotalEvents] = useState(0);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [eventType, setEventType] = useState("ALL");
  const [status, setStatus] = useState("ALL");
  const [usernameFilter, setUsernameFilter] = useState("");
  const [limit, setLimit] = useState(200);
  const [expandedRow, setExpandedRow] = useState<number | null>(null);

  const fetchLogs = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const params: any = { limit };
      if (eventType !== "ALL") params.event_type = eventType;
      if (status !== "ALL") params.status = status;
      if (usernameFilter.trim()) params.username = usernameFilter.trim();

      const [logsRes, summaryRes] = await Promise.all([
        api.get("/logs/", { params }),
        api.get("/logs/summary"),
      ]);
      setLogs(logsRes.data.logs || []);
      setSummary(summaryRes.data.summary || {});
      setTotalEvents(summaryRes.data.total_events || 0);
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Failed to fetch logs.");
    } finally {
      setIsLoading(false);
    }
  }, [eventType, status, usernameFilter, limit]);

  useEffect(() => { fetchLogs(); }, [fetchLogs]);

  // Auto-refresh every 30s
  useEffect(() => {
    const id = setInterval(fetchLogs, 30000);
    return () => clearInterval(id);
  }, [fetchLogs]);

  const summaryCards = [
    { label: "Total Events",    value: totalEvents,                                                         color: "text-indigo-300",  bg: "from-indigo-500/10 to-indigo-600/5" },
    { label: "Logins",          value: (summary["LOGIN"]?.total || 0),                                      color: "text-emerald-300", bg: "from-emerald-500/10 to-emerald-600/5" },
    { label: "Errors",          value: Object.values(summary).reduce((s, v) => s + (v.ERROR || 0), 0),      color: "text-red-300",     bg: "from-red-500/10 to-red-600/5" },
    { label: "API Calls",       value: (summary["API_CALL"]?.total || 0),                                   color: "text-sky-300",     bg: "from-sky-500/10 to-sky-600/5" },
    { label: "Admin Actions",   value: (summary["ADMIN_ACTION"]?.total || 0),                               color: "text-amber-300",   bg: "from-amber-500/10 to-amber-600/5" },
    { label: "Stock Updates",   value: (summary["STOCK_UPDATED"]?.total || 0),                              color: "text-cyan-300",    bg: "from-cyan-500/10 to-cyan-600/5" },
    { label: "Baseline Changes",value: (summary["BASELINE_STOCK_CHANGED"]?.total || 0),                     color: "text-violet-300",  bg: "from-violet-500/10 to-violet-600/5" },
    { label: "Pwd Changes",     value: (summary["PASSWORD_CHANGED"]?.total || 0),                           color: "text-amber-300",   bg: "from-amber-500/10 to-amber-600/5" },
    { label: "Emails Sent",     value: (summary["EMAIL_SENT"]?.total || 0),                                 color: "text-teal-300",    bg: "from-teal-500/10 to-teal-600/5" },
    { label: "Sim Actions",     value: (summary["SIM_ACTION"]?.total || 0),                                 color: "text-purple-300",  bg: "from-purple-500/10 to-purple-600/5" },
  ];

  return (
    <div className="space-y-6 animate-fade-in-up">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500/20 to-purple-500/20 border border-indigo-500/30 flex items-center justify-center">
            <Terminal size={20} className="text-indigo-300" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-white">System Activity Logs</h1>
            <p className="text-slate-400 text-sm">Real-time audit trail — logins, API calls, errors, admin & simulation actions</p>
          </div>
        </div>
        <button
          onClick={fetchLogs}
          disabled={isLoading}
          className="flex items-center gap-2 px-4 py-2 rounded-xl bg-indigo-500/20 border border-indigo-500/30 text-indigo-300 hover:bg-indigo-500/30 transition-all text-sm font-medium disabled:opacity-50"
        >
          <RefreshCw size={14} className={isLoading ? "animate-spin" : ""} />
          {isLoading ? "Refreshing…" : "Refresh"}
        </button>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
        {summaryCards.map((c) => (
          <div key={c.label} className={`bg-gradient-to-br ${c.bg} border border-white/10 rounded-xl p-3 space-y-1`}>
            <p className="text-[10px] text-slate-400 uppercase tracking-wider font-semibold">{c.label}</p>
            <p className={`text-2xl font-black ${c.color}`}>{c.value.toLocaleString()}</p>
          </div>
        ))}
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-3 p-4 bg-white/5 border border-white/10 rounded-xl">
        <Filter size={14} className="text-slate-400 shrink-0" />

        {/* Event Type */}
        <div className="relative">
          <select
            value={eventType}
            onChange={(e) => setEventType(e.target.value)}
            className="appearance-none pl-3 pr-8 py-1.5 rounded-lg bg-white/10 border border-white/20 text-slate-200 text-xs focus:outline-none focus:border-indigo-400 cursor-pointer"
          >
            {EVENT_TYPES.map((t) => (
              <option key={t} value={t} className="bg-slate-900">{t === "ALL" ? "All Event Types" : t}</option>
            ))}
          </select>
          <ChevronDown size={12} className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none" />
        </div>

        {/* Status */}
        <div className="relative">
          <select
            value={status}
            onChange={(e) => setStatus(e.target.value)}
            className="appearance-none pl-3 pr-8 py-1.5 rounded-lg bg-white/10 border border-white/20 text-slate-200 text-xs focus:outline-none focus:border-indigo-400 cursor-pointer"
          >
            {STATUSES.map((s) => (
              <option key={s} value={s} className="bg-slate-900">{s === "ALL" ? "All Statuses" : s}</option>
            ))}
          </select>
          <ChevronDown size={12} className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none" />
        </div>

        {/* Username search */}
        <div className="relative">
          <Search size={12} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-500" />
          <input
            type="text"
            placeholder="Search username…"
            value={usernameFilter}
            onChange={(e) => setUsernameFilter(e.target.value)}
            className="pl-7 pr-3 py-1.5 rounded-lg bg-white/10 border border-white/20 text-slate-200 text-xs placeholder:text-slate-500 focus:outline-none focus:border-indigo-400 w-40"
          />
        </div>

        {/* Limit */}
        <div className="relative ml-auto">
          <select
            value={limit}
            onChange={(e) => setLimit(Number(e.target.value))}
            className="appearance-none pl-3 pr-8 py-1.5 rounded-lg bg-white/10 border border-white/20 text-slate-200 text-xs focus:outline-none focus:border-indigo-400 cursor-pointer"
          >
            {[50, 100, 200, 500, 1000].map((n) => (
              <option key={n} value={n} className="bg-slate-900">Last {n}</option>
            ))}
          </select>
          <ChevronDown size={12} className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none" />
        </div>

        <span className="text-xs text-slate-400">{logs.length} entries shown</span>
      </div>

      {/* Error */}
      {error && (
        <div className="flex items-center gap-2 p-3 bg-red-500/10 border border-red-500/30 rounded-xl text-red-400 text-sm">
          <XCircle size={16} />
          {error}
        </div>
      )}

      {/* Logs Table */}
      <div className="bg-white/5 border border-white/10 rounded-2xl overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-white/10 text-left">
                <th className="px-4 py-3 text-[10px] uppercase tracking-widest text-slate-500 font-semibold whitespace-nowrap">Timestamp</th>
                <th className="px-4 py-3 text-[10px] uppercase tracking-widest text-slate-500 font-semibold whitespace-nowrap">Event</th>
                <th className="px-4 py-3 text-[10px] uppercase tracking-widest text-slate-500 font-semibold whitespace-nowrap">Status</th>
                <th className="px-4 py-3 text-[10px] uppercase tracking-widest text-slate-500 font-semibold whitespace-nowrap">User</th>
                <th className="px-4 py-3 text-[10px] uppercase tracking-widest text-slate-500 font-semibold whitespace-nowrap">Role</th>
                <th className="px-4 py-3 text-[10px] uppercase tracking-widest text-slate-500 font-semibold">Message</th>
              </tr>
            </thead>
            <tbody>
              {isLoading && logs.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-4 py-16 text-center text-slate-400">
                    <RefreshCw size={24} className="animate-spin mx-auto mb-3 text-indigo-400" />
                    Loading logs…
                  </td>
                </tr>
              ) : logs.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-4 py-16 text-center text-slate-500">
                    <Terminal size={32} className="mx-auto mb-3 opacity-30" />
                    <p>No log entries found.</p>
                    <p className="text-xs mt-1">Activity will appear here as users interact with the system.</p>
                  </td>
                </tr>
              ) : (
                logs.map((log, idx) => {
                  const EventIcon = EVENT_ICONS[log.event_type] || Info;
                  const StatusIcon = STATUS_ICONS[log.status] || Info;
                  const isExpanded = expandedRow === idx;

                  return (
                    <>
                      <tr
                        key={idx}
                        onClick={() => setExpandedRow(isExpanded ? null : idx)}
                        className={`border-b border-white/5 hover:bg-white/5 transition-colors cursor-pointer ${idx % 2 === 0 ? '' : 'bg-white/[0.02]'}`}
                      >
                        {/* Timestamp */}
                        <td className="px-4 py-2.5 whitespace-nowrap">
                          <span className="text-xs font-mono text-slate-400">{formatTime(log.created_at)}</span>
                        </td>

                        {/* Event Type */}
                        <td className="px-4 py-2.5">
                          <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md text-[10px] font-bold uppercase tracking-wide ${EVENT_TYPE_COLORS[log.event_type] || "text-slate-300 bg-slate-500/10"}`}>
                            <EventIcon size={10} />
                            {log.event_type}
                          </span>
                        </td>

                        {/* Status */}
                        <td className="px-4 py-2.5">
                          <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold border ${STATUS_COLORS[log.status] || STATUS_COLORS.INFO}`}>
                            <StatusIcon size={10} />
                            {log.status}
                          </span>
                        </td>

                        {/* Username */}
                        <td className="px-4 py-2.5">
                          <span className="text-xs font-mono text-white font-semibold">{log.username}</span>
                        </td>

                        {/* Role */}
                        <td className="px-4 py-2.5">
                          <span className="text-[10px] text-slate-400 uppercase tracking-wide">{log.user_role}</span>
                        </td>

                        {/* Message */}
                        <td className="px-4 py-2.5 max-w-[420px]">
                          <p className="text-xs text-slate-300 truncate">{log.message}</p>
                          {log.detail && (
                            <p className="text-[10px] text-slate-500 truncate">{log.detail}</p>
                          )}
                        </td>
                      </tr>

                      {/* Expanded detail row */}
                      {isExpanded && (
                        <tr key={`${idx}-expand`} className="bg-indigo-500/5 border-b border-white/10">
                          <td colSpan={6} className="px-6 py-3 space-y-1">
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-xs text-slate-400">
                              {log.ip_address && <span><span className="text-slate-500">IP:</span> {log.ip_address}</span>}
                              {log.user_agent && <span className="truncate"><span className="text-slate-500">UA:</span> {log.user_agent}</span>}
                              {log.detail && <span className="col-span-2"><span className="text-slate-500">Detail:</span> {log.detail}</span>}
                            </div>
                          </td>
                        </tr>
                      )}
                    </>
                  );
                })
              )}
            </tbody>
          </table>
        </div>

        {/* Footer */}
        {logs.length > 0 && (
          <div className="px-4 py-3 border-t border-white/5 flex items-center justify-between">
            <span className="text-xs text-slate-500">Showing {logs.length} of {totalEvents} total events • Auto-refreshes every 30s</span>
            <span className="text-xs text-slate-600 font-mono">Click a row to expand details</span>
          </div>
        )}
      </div>
    </div>
  );
}
