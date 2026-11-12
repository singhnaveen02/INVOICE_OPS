import React, { useState, useEffect } from 'react';
import { ClipboardList, Plus, Search, ChevronDown, ChevronUp } from 'lucide-react';
import { api } from '../api/client';
import { formatCurrency, formatPercent, formatDate } from '../utils/format';
import LoadingSpinner from '../components/LoadingSpinner';
import EmptyState from '../components/EmptyState';

export default function PurchaseOrders() {
  const [pos, setPos] = useState([]);
  const [statusFilter, setStatusFilter] = useState('');
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);
  const [expandedPoId, setExpandedPoId] = useState(null);

  const fetchPOs = async () => {
    try {
      setLoading(true);
      const params = {};
      if (statusFilter) params.status = statusFilter;
      if (search) params.search = search;
      const res = await api.listPOs(params);
      setPos(res.data || []);
    } catch (err) {
      console.error('Failed to load POs:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPOs();
  }, [statusFilter]);

  const toggleExpand = (id) => {
    setExpandedPoId(expandedPoId === id ? null : id);
  };

  return (
    <div className="space-y-6">
      {/* Title */}
      <div>
        <h2 className="text-2xl font-bold text-slate-900 tracking-tight">Purchase Order Registry</h2>
        <p className="text-sm text-slate-500 mt-1">
          Master contracts, authorized line items, and cumulative budget utilization limits.
        </p>
      </div>

      {/* Filter and Search */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex flex-wrap items-center justify-between gap-4">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            fetchPOs();
          }}
          className="flex items-center gap-3 flex-1 max-w-md"
        >
          <div className="relative flex-1">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search PO # or description..."
              className="w-full text-xs pl-9 pr-4 py-2 rounded-lg border border-slate-200 focus:outline-none"
            />
          </div>
          <button
            type="submit"
            className="bg-slate-900 text-white text-xs font-semibold px-4 py-2 rounded-lg"
          >
            Search
          </button>
        </form>

        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="text-xs py-2 px-3 rounded-lg border border-slate-200 bg-white text-slate-700"
        >
          <option value="">All Statuses</option>
          <option value="OPEN">Open</option>
          <option value="PARTIAL">Partial</option>
          <option value="CLOSED">Closed</option>
          <option value="CANCELLED">Cancelled</option>
        </select>
      </div>

      {/* PO List */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        {loading ? (
          <LoadingSpinner message="Loading purchase orders..." />
        ) : pos.length === 0 ? (
          <EmptyState title="No purchase orders found" description="Try clearing your filters." />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 text-slate-500 uppercase font-semibold border-b border-slate-100">
                <tr>
                  <th className="py-3 px-4">PO Number</th>
                  <th className="py-3 px-4">Total Amount</th>
                  <th className="py-3 px-4">Utilized</th>
                  <th className="py-3 px-4">Remaining</th>
                  <th className="py-3 px-4 w-44">Utilization %</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4">Issue Date</th>
                  <th className="py-3 px-4 text-right">Items</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-slate-700 font-medium">
                {pos.map((po) => {
                  const total = po.total_amount || 0.01;
                  const utilized = po.utilized_amount || 0;
                  const pct = Math.min(100, (utilized / total) * 100);
                  const isExpanded = expandedPoId === po.id;

                  return (
                    <React.Fragment key={po.id}>
                      <tr className="hover:bg-slate-50/70 transition-colors">
                        <td className="py-3.5 px-4 font-bold text-slate-900 font-mono">
                          {po.po_number}
                        </td>
                        <td className="py-3.5 px-4 font-bold text-slate-900">
                          {formatCurrency(po.total_amount, po.currency)}
                        </td>
                        <td className="py-3.5 px-4 text-slate-700">
                          {formatCurrency(po.utilized_amount, po.currency)}
                        </td>
                        <td className="py-3.5 px-4 font-semibold text-emerald-700">
                          {formatCurrency(po.remaining_amount, po.currency)}
                        </td>
                        <td className="py-3.5 px-4">
                          <div className="space-y-1">
                            <div className="flex justify-between text-[10px] font-mono text-slate-500">
                              <span>{formatPercent(pct)}</span>
                            </div>
                            <div className="w-full h-2 rounded-full bg-slate-100 overflow-hidden">
                              <div
                                className={`h-full rounded-full transition-all ${
                                  pct >= 100
                                    ? 'bg-rose-500'
                                    : pct >= 80
                                    ? 'bg-amber-500'
                                    : 'bg-emerald-500'
                                }`}
                                style={{ width: `${pct}%` }}
                              />
                            </div>
                          </div>
                        </td>
                        <td className="py-3.5 px-4">
                          <span
                            className={`text-xs font-semibold px-2.5 py-0.5 rounded-full ${
                              po.status === 'OPEN'
                                ? 'bg-sky-50 text-sky-700 border border-sky-200'
                                : po.status === 'PARTIAL'
                                ? 'bg-amber-50 text-amber-700 border border-amber-200'
                                : po.status === 'CLOSED'
                                ? 'bg-slate-100 text-slate-700 border border-slate-200'
                                : 'bg-rose-50 text-rose-700 border border-rose-200'
                            }`}
                          >
                            {po.status}
                          </span>
                        </td>
                        <td className="py-3.5 px-4 text-slate-500">
                          {formatDate(po.issue_date)}
                        </td>
                        <td className="py-3.5 px-4 text-right">
                          <button
                            onClick={() => toggleExpand(po.id)}
                            className="p-1.5 rounded hover:bg-slate-100 text-slate-500"
                            title="Expand line items"
                          >
                            {isExpanded ? (
                              <ChevronUp className="w-4 h-4" />
                            ) : (
                              <ChevronDown className="w-4 h-4" />
                            )}
                          </button>
                        </td>
                      </tr>

                      {/* Expandable Line Items Row */}
                      {isExpanded && (
                        <tr className="bg-slate-50/50">
                          <td colSpan={8} className="p-4">
                            <div className="bg-white rounded-lg border border-slate-200 p-4">
                              <h4 className="text-xs font-bold text-slate-800 mb-2">
                                Authorized Line Items: {po.po_number}
                              </h4>
                              {po.line_items && po.line_items.length > 0 ? (
                                <table className="w-full text-xs text-left">
                                  <thead className="bg-slate-50 text-slate-500">
                                    <tr>
                                      <th className="p-2">#</th>
                                      <th className="p-2">Description</th>
                                      <th className="p-2">SKU</th>
                                      <th className="p-2 text-right">Qty</th>
                                      <th className="p-2 text-right">Unit Price</th>
                                      <th className="p-2 text-right">Total Price</th>
                                    </tr>
                                  </thead>
                                  <tbody className="divide-y divide-slate-100 text-slate-600">
                                    {po.line_items.map((item) => (
                                      <tr key={item.id}>
                                        <td className="p-2">{item.line_number}</td>
                                        <td className="p-2 font-medium text-slate-800">{item.description}</td>
                                        <td className="p-2 font-mono">{item.sku || '—'}</td>
                                        <td className="p-2 text-right">{item.quantity}</td>
                                        <td className="p-2 text-right font-mono">{formatCurrency(item.unit_price)}</td>
                                        <td className="p-2 text-right font-bold text-slate-900 font-mono">
                                          {formatCurrency(item.total_price)}
                                        </td>
                                      </tr>
                                    ))}
                                  </tbody>
                                </table>
                              ) : (
                                <p className="text-xs text-slate-400">
                                  Contract description: {po.description || 'General procurement services'}
                                </p>
                              )}
                            </div>
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
