import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { AlertTriangle, ArrowRight, FileText, CheckCircle2 } from 'lucide-react';
import { api } from '../api/client';
import StatusBadge from '../components/StatusBadge';
import { formatCurrency, formatDate } from '../utils/format';
import LoadingSpinner from '../components/LoadingSpinner';
import EmptyState from '../components/EmptyState';

export default function ReviewQueue() {
  const [invoices, setInvoices] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchQueue = async () => {
    try {
      setLoading(true);
      const res = await api.getReviewQueue();
      setInvoices(res.data || []);
    } catch (err) {
      console.error('Failed to load review queue:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchQueue();
  }, []);

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-2xl font-bold text-slate-900 tracking-tight">
              Human Review Queue
            </h2>
            <span className="bg-amber-100 text-amber-800 font-bold text-xs px-2.5 py-0.5 rounded-full">
              {invoices.length} Pending
            </span>
          </div>
          <p className="text-sm text-slate-500 mt-1">
            Invoices routed to AP personnel due to missing fields, low extraction confidence, or ambiguous matching.
          </p>
        </div>
      </div>

      {loading ? (
        <LoadingSpinner message="Loading review queue..." />
      ) : invoices.length === 0 ? (
        <EmptyState
          title="Review Queue is Empty"
          description="Great job! All ingested invoices have passed automated business checks or been resolved."
          icon={CheckCircle2}
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {invoices.map((inv) => (
            <div
              key={inv.id}
              className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm hover:border-amber-300 transition-all flex flex-col justify-between"
            >
              <div>
                <div className="flex items-start justify-between mb-3">
                  <div className="truncate pr-2">
                    <span className="text-xs font-bold text-slate-900 block truncate">
                      {inv.invoice_number || inv.original_filename}
                    </span>
                    <span className="text-[11px] text-slate-400">
                      {formatDate(inv.created_at)}
                    </span>
                  </div>
                  <StatusBadge status="REVIEW" size="sm" />
                </div>

                <div className="space-y-2 py-3 border-t border-slate-100 text-xs">
                  <div className="flex justify-between">
                    <span className="text-slate-500">Stated Vendor:</span>
                    <span className="font-semibold text-slate-800 truncate max-w-[150px]">
                      {inv.vendor_name_extracted || 'Unidentified'}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-500">Stated PO:</span>
                    <span className="font-mono text-slate-700">
                      {inv.po_number_extracted || 'None'}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-500">Total Value:</span>
                    <span className="font-bold text-slate-900">
                      {formatCurrency(inv.grand_total, inv.currency)}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-500">Confidence:</span>
                    <span className="font-mono text-amber-600 font-bold">
                      {(inv.extraction_confidence * 100).toFixed(0)}%
                    </span>
                  </div>
                </div>
              </div>

              <div className="mt-4 pt-3 border-t border-slate-100">
                <Link
                  to={`/review/${inv.id}`}
                  className="w-full inline-flex items-center justify-center gap-2 bg-amber-600 hover:bg-amber-700 text-white text-xs font-semibold py-2 rounded-lg transition-colors shadow-sm"
                >
                  <span>Review &amp; Resolve</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </Link>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
