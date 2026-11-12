import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  Search,
  Filter,
  Download,
  Eye,
  Trash2,
  ChevronLeft,
  ChevronRight,
  FileText,
  AlertCircle,
} from 'lucide-react';
import { api } from '../api/client';
import StatusBadge from '../components/StatusBadge';
import { formatCurrency, formatDate } from '../utils/format';
import LoadingSpinner from '../components/LoadingSpinner';
import EmptyState from '../components/EmptyState';

export default function InvoiceList() {
  const [invoices, setInvoices] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const pageSize = 15;

  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [loading, setLoading] = useState(true);

  const fetchInvoices = async () => {
    setLoading(true);
    try {
      const params = {
        page,
        page_size: pageSize,
      };
      if (search) params.search = search;
      if (statusFilter) params.status = statusFilter;
      if (dateFrom) params.date_from = dateFrom;
      if (dateTo) params.date_to = dateTo;

      const res = await api.listInvoices(params);
      setInvoices(res.data.items || []);
      setTotal(res.data.total || 0);
    } catch (err) {
      console.error('Failed to load invoices:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchInvoices();
  }, [page, statusFilter, dateFrom, dateTo]);

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    setPage(1);
    fetchInvoices();
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Are you sure you want to delete this invoice?')) return;
    try {
      await api.deleteInvoice(id);
      fetchInvoices();
    } catch (err) {
      alert('Delete failed');
    }
  };

  const totalPages = Math.ceil(total / pageSize) || 1;

  return (
    <div className="space-y-6">
      {/* Header & Export */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold text-slate-900 tracking-tight">Invoice History</h2>
          <p className="text-sm text-slate-500 mt-1">
            Complete searchable repository of all ingested invoices and decisions.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <a
            href={api.exportInvoicesUrl({ status: statusFilter })}
            download="invoices_export.csv"
            className="inline-flex items-center gap-2 bg-white hover:bg-slate-50 border border-slate-200 text-slate-700 text-xs font-semibold px-4 py-2.5 rounded-lg shadow-sm transition-colors"
          >
            <Download className="w-4 h-4 text-slate-500" />
            <span>Export CSV</span>
          </a>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm space-y-3">
        <form onSubmit={handleSearchSubmit} className="flex flex-wrap items-center gap-3">
          {/* Search Input */}
          <div className="relative flex-1 min-w-[240px]">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search invoice #, vendor, PO number..."
              className="w-full text-xs pl-9 pr-4 py-2 rounded-lg border border-slate-200 focus:outline-none focus:ring-1 focus:ring-sky-500"
            />
          </div>

          {/* Status Dropdown */}
          <select
            value={statusFilter}
            onChange={(e) => {
              setStatusFilter(e.target.value);
              setPage(1);
            }}
            className="text-xs py-2 px-3 rounded-lg border border-slate-200 bg-white text-slate-700 focus:outline-none"
          >
            <option value="">All Statuses</option>
            <option value="APPROVED">Approved</option>
            <option value="REVIEW">Needs Review</option>
            <option value="REJECTED">Rejected</option>
            <option value="PROCESSING">Processing</option>
          </select>

          {/* Date Range */}
          <input
            type="date"
            value={dateFrom}
            onChange={(e) => setDateFrom(e.target.value)}
            className="text-xs py-2 px-3 rounded-lg border border-slate-200 text-slate-700 focus:outline-none"
            title="From Date"
          />
          <input
            type="date"
            value={dateTo}
            onChange={(e) => setDateTo(e.target.value)}
            className="text-xs py-2 px-3 rounded-lg border border-slate-200 text-slate-700 focus:outline-none"
            title="To Date"
          />

          <button
            type="submit"
            className="bg-slate-900 hover:bg-slate-800 text-white text-xs font-semibold px-4 py-2 rounded-lg transition-colors"
          >
            Filter
          </button>
        </form>
      </div>

      {/* Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        {loading ? (
          <LoadingSpinner message="Loading invoice records..." />
        ) : invoices.length === 0 ? (
          <EmptyState
            title="No invoices match your query"
            description="Try adjusting your status filter or search parameters."
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50/80 text-slate-500 uppercase tracking-wider font-semibold border-b border-slate-100">
                <tr>
                  <th className="py-3 px-4">Invoice #</th>
                  <th className="py-3 px-4">Vendor</th>
                  <th className="py-3 px-4">Date</th>
                  <th className="py-3 px-4">Matched PO</th>
                  <th className="py-3 px-4">Total Amount</th>
                  <th className="py-3 px-4">Confidence</th>
                  <th className="py-3 px-4">Decision</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-slate-700 font-medium">
                {invoices.map((inv) => (
                  <tr key={inv.id} className="hover:bg-slate-50/70 transition-colors">
                    <td className="py-3.5 px-4">
                      <Link
                        to={`/invoices/${inv.id}`}
                        className="font-bold text-sky-600 hover:underline"
                      >
                        {inv.invoice_number || inv.original_filename}
                      </Link>
                      {inv.is_duplicate && (
                        <span className="block text-[10px] text-rose-600 font-semibold mt-0.5">
                          DUPLICATE
                        </span>
                      )}
                    </td>
                    <td className="py-3.5 px-4 text-slate-900">
                      {inv.vendor_name_extracted || '—'}
                    </td>
                    <td className="py-3.5 px-4 text-slate-500">
                      {formatDate(inv.invoice_date)}
                    </td>
                    <td className="py-3.5 px-4 font-mono text-[11px] text-slate-600">
                      {inv.po_number_extracted || '—'}
                    </td>
                    <td className="py-3.5 px-4 font-bold text-slate-900">
                      {formatCurrency(inv.grand_total, inv.currency)}
                    </td>
                    <td className="py-3.5 px-4 font-mono text-slate-500">
                      {(inv.extraction_confidence * 100).toFixed(0)}%
                    </td>
                    <td className="py-3.5 px-4">
                      <StatusBadge status={inv.status} size="sm" />
                    </td>
                    <td className="py-3.5 px-4 text-right">
                      <div className="flex items-center justify-end gap-2">
                        <Link
                          to={`/invoices/${inv.id}`}
                          className="p-1.5 text-slate-500 hover:text-sky-600 rounded hover:bg-slate-100"
                          title="View Details"
                        >
                          <Eye className="w-4 h-4" />
                        </Link>
                        <button
                          onClick={() => handleDelete(inv.id)}
                          className="p-1.5 text-slate-400 hover:text-rose-600 rounded hover:bg-slate-100"
                          title="Delete"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination Footer */}
        {total > pageSize && (
          <div className="p-4 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500">
            <span>
              Showing {(page - 1) * pageSize + 1} to {Math.min(page * pageSize, total)} of {total} records
            </span>
            <div className="flex items-center gap-2">
              <button
                disabled={page <= 1}
                onClick={() => setPage(page - 1)}
                className="p-1.5 rounded border border-slate-200 disabled:opacity-40 hover:bg-slate-50"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
              <span className="font-semibold text-slate-700">
                Page {page} of {totalPages}
              </span>
              <button
                disabled={page >= totalPages}
                onClick={() => setPage(page + 1)}
                className="p-1.5 rounded border border-slate-200 disabled:opacity-40 hover:bg-slate-50"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
