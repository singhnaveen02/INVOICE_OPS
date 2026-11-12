import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  FileText,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Clock,
  DollarSign,
  CopyX,
  TrendingUp,
  ArrowRight,
  ShieldAlert,
} from 'lucide-react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
} from 'recharts';
import { api } from '../api/client';
import { formatCurrency, formatDuration, formatPercent, formatDate } from '../utils/format';
import LoadingSpinner from '../components/LoadingSpinner';

export default function Dashboard() {
  const [stats, setStats] = useState(null);
  const [trends, setTrends] = useState([]);
  const [distribution, setDistribution] = useState([]);
  const [poUtilization, setPoUtilization] = useState([]);
  const [recentActivity, setRecentActivity] = useState([]);
  const [loading, setLoading] = useState(true);

  const loadDashboardData = async () => {
    try {
      setLoading(true);
      const [sRes, tRes, dRes, pRes, rRes] = await Promise.all([
        api.getStats(),
        api.getTrends(),
        api.getStatusDistribution(),
        api.getPOUtilization(),
        api.getRecentActivity(),
      ]);
      setStats(sRes.data);
      setTrends(tRes.data);
      setDistribution(dRes.data);
      setPoUtilization(pRes.data);
      setRecentActivity(rRes.data);
    } catch (err) {
      console.error('Failed to load dashboard:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDashboardData();
  }, []);

  if (loading && !stats) {
    return <LoadingSpinner message="Calculating financial metrics and AP status..." />;
  }

  const kpis = [
    {
      title: 'Total Invoices',
      value: stats?.total_invoices || 0,
      sub: `${formatCurrency(stats?.total_value || 0)} Total Value`,
      icon: FileText,
      color: 'bg-slate-100 text-slate-800',
    },
    {
      title: 'Approved for Payment',
      value: stats?.approved_invoices || 0,
      sub: `${formatCurrency(stats?.approved_value || 0)} Approved`,
      icon: CheckCircle2,
      color: 'bg-emerald-50 text-emerald-700 border-emerald-100',
    },
    {
      title: 'Pending Human Review',
      value: stats?.pending_review || 0,
      sub: 'Action required in queue',
      icon: AlertTriangle,
      color: 'bg-amber-50 text-amber-700 border-amber-100',
      link: '/review',
    },
    {
      title: 'Policy Rejections',
      value: stats?.rejected_invoices || 0,
      sub: `${stats?.duplicate_count || 0} Duplicates blocked`,
      icon: XCircle,
      color: 'bg-rose-50 text-rose-700 border-rose-100',
    },
  ];

  return (
    <div className="space-y-8">
      {/* Page Title */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold text-slate-900 tracking-tight">
            Accounts Payable Overview
          </h2>
          <p className="text-sm text-slate-500 mt-1">
            Automated invoice verification, 3-way PO reconciliation, and policy auditing.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Link
            to="/upload"
            className="inline-flex items-center gap-2 bg-sky-600 hover:bg-sky-700 text-white text-xs font-semibold px-4 py-2.5 rounded-lg shadow-sm transition-colors"
          >
            <span>Upload Invoice</span>
            <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </div>

      {/* KPI Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {kpis.map((kpi, idx) => {
          const Icon = kpi.icon;
          return (
            <div
              key={idx}
              className={`p-5 rounded-xl border bg-white shadow-sm flex flex-col justify-between ${
                kpi.link ? 'hover:border-amber-300 transition-colors' : ''
              }`}
            >
              <div className="flex items-start justify-between">
                <div>
                  <span className="text-xs font-medium text-slate-500 uppercase tracking-wider">
                    {kpi.title}
                  </span>
                  <p className="text-2xl font-bold text-slate-900 mt-1.5">{kpi.value}</p>
                </div>
                <div className={`p-2.5 rounded-lg ${kpi.color}`}>
                  <Icon className="w-5 h-5" />
                </div>
              </div>
              <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500">
                <span>{kpi.sub}</span>
                {kpi.link && (
                  <Link to={kpi.link} className="font-semibold text-amber-600 hover:underline">
                    View Queue &rarr;
                  </Link>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Analytics Second Row: Trend Chart & Status Pie */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Invoice Processing Volume (Line Chart) */}
        <div className="lg:col-span-2 bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h3 className="text-sm font-bold text-slate-900">Invoice Ingestion Trends</h3>
              <p className="text-xs text-slate-500 mt-0.5">Daily volume over past 30 days</p>
            </div>
            <div className="flex items-center gap-4 text-xs">
              <span className="flex items-center gap-1.5 text-slate-600">
                <span className="w-2.5 h-2.5 rounded-full bg-sky-500" /> Total Invoices
              </span>
              <span className="flex items-center gap-1.5 text-slate-600">
                <span className="w-2.5 h-2.5 rounded-full bg-emerald-500" /> Approved
              </span>
            </div>
          </div>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={trends}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                <XAxis
                  dataKey="date"
                  tickFormatter={(d) => d.slice(5)}
                  tick={{ fontSize: 11, fill: '#64748b' }}
                  stroke="#cbd5e1"
                />
                <YAxis allowDecimals={false} tick={{ fontSize: 11, fill: '#64748b' }} stroke="#cbd5e1" />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#0f172a',
                    borderRadius: '8px',
                    border: 'none',
                    color: '#fff',
                    fontSize: '12px',
                  }}
                />
                <Line
                  type="monotone"
                  dataKey="total"
                  stroke="#0284c7"
                  strokeWidth={2.5}
                  dot={false}
                  name="Total"
                />
                <Line
                  type="monotone"
                  dataKey="approved"
                  stroke="#10b981"
                  strokeWidth={2}
                  dot={false}
                  name="Approved"
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Status Breakdown (Pie Chart) */}
        <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm flex flex-col justify-between">
          <div>
            <h3 className="text-sm font-bold text-slate-900">Decision Distribution</h3>
            <p className="text-xs text-slate-500 mt-0.5">Automated policy outcomes</p>
          </div>

          <div className="h-48 my-2">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={distribution}
                  dataKey="count"
                  nameKey="status"
                  cx="50%"
                  cy="50%"
                  innerRadius={50}
                  outerRadius={75}
                  paddingAngle={3}
                >
                  {distribution.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#0f172a',
                    borderRadius: '8px',
                    border: 'none',
                    color: '#fff',
                    fontSize: '12px',
                  }}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>

          <div className="space-y-1.5 border-t border-slate-100 pt-3 text-xs">
            {distribution.map((d) => (
              <div key={d.status} className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: d.color }} />
                  <span className="text-slate-600 capitalize">{d.status}</span>
                </div>
                <span className="font-semibold text-slate-900">{d.count}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Third Row: PO Utilization & Recent Activity */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Purchase Order Budget Utilization */}
        <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-sm font-bold text-slate-900">Purchase Order Utilization</h3>
              <p className="text-xs text-slate-500 mt-0.5">Cumulative billing vs approved budget</p>
            </div>
            <Link to="/purchase-orders" className="text-xs font-semibold text-sky-600 hover:underline">
              View All POs &rarr;
            </Link>
          </div>

          <div className="space-y-3.5">
            {poUtilization.slice(0, 5).map((po) => (
              <div key={po.po_id} className="text-xs">
                <div className="flex items-center justify-between mb-1">
                  <div>
                    <span className="font-semibold text-slate-800">{po.po_number}</span>
                    <span className="text-slate-400 ml-1.5">({po.vendor_name})</span>
                  </div>
                  <span className="font-mono font-semibold text-slate-700">
                    {formatPercent(po.utilization_pct)}
                  </span>
                </div>
                <div className="w-full h-2 rounded-full bg-slate-100 overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all ${
                      po.utilization_pct >= 95
                        ? 'bg-rose-500'
                        : po.utilization_pct >= 75
                        ? 'bg-amber-500'
                        : 'bg-emerald-500'
                    }`}
                    style={{ width: `${Math.min(100, po.utilization_pct)}%` }}
                  />
                </div>
                <div className="flex justify-between text-[11px] text-slate-400 mt-1">
                  <span>Utilized: {formatCurrency(po.utilized_amount)}</span>
                  <span>Budget: {formatCurrency(po.total_amount)}</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Audit Trail & Live Activity Feed */}
        <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-sm font-bold text-slate-900">Audit Trail &amp; Activity</h3>
              <p className="text-xs text-slate-500 mt-0.5">Recent system decisions and reviewer overrides</p>
            </div>
            <span className="text-[11px] bg-slate-100 text-slate-600 px-2 py-0.5 rounded font-mono">
              Avg {stats?.avg_processing_time_ms || 450}ms / inv
            </span>
          </div>

          <div className="space-y-3">
            {recentActivity.slice(0, 6).map((act, i) => (
              <div
                key={i}
                className="flex items-start justify-between p-2.5 rounded-lg bg-slate-50 border border-slate-100 text-xs"
              >
                <div>
                  <p className="font-semibold text-slate-800">{act.action}</p>
                  <p className="text-slate-500 text-[11px] mt-0.5">{act.notes}</p>
                </div>
                <div className="text-right text-[11px] text-slate-400 flex-shrink-0 ml-3">
                  <p className="font-medium text-slate-600">{act.actor}</p>
                  <p>{formatDate(act.timestamp)}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
