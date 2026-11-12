import React from 'react';
import { CheckCircle2, AlertTriangle, XCircle, Info } from 'lucide-react';

const RULE_TITLES = {
  vendor_approval: '1. Vendor Approval Status',
  mandatory_fields: '2. Mandatory Invoice Fields',
  duplicate_detection: '3. Duplicate Submission Detection',
  vendor_po_match: '4. Vendor & PO Cross-Match',
  po_status: '5. Purchase Order Status Check',
  amount_vs_po: '6. Invoice vs PO Amount Tolerance',
  line_item_check: '7. Line Item Discrepancies',
  tax_reconciliation: '8. Tax & Subtotal Reconciliation',
  currency_check: '9. Currency Compatibility',
  po_utilization: '10. Cumulative PO Utilization',
  date_consistency: '11. Invoice & PO Date Consistency',
};

export default function ValidationChecklist({ results = [] }) {
  if (!results || results.length === 0) {
    return (
      <div className="text-center py-6 text-sm text-slate-500 bg-slate-50 rounded-lg border border-dashed border-slate-200">
        No validation checks recorded yet.
      </div>
    );
  }

  return (
    <div className="space-y-2.5">
      {results.map((res, idx) => {
        const isPassed = res.passed;
        const isCritical = res.severity === 'CRITICAL';
        const isError = res.severity === 'ERROR';
        const isWarning = res.severity === 'WARNING';

        const title = RULE_TITLES[res.rule_name] || res.rule_name;

        return (
          <div
            key={idx}
            className={`p-3 rounded-lg border text-sm flex items-start justify-between gap-3 transition-colors ${
              isPassed
                ? 'bg-emerald-50/50 border-emerald-100'
                : isCritical
                ? 'bg-rose-50 border-rose-200'
                : isError
                ? 'bg-rose-50/60 border-rose-100'
                : 'bg-amber-50/60 border-amber-100'
            }`}
          >
            <div className="flex items-start gap-2.5 flex-1">
              <div className="mt-0.5 flex-shrink-0">
                {isPassed ? (
                  <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                ) : isCritical || isError ? (
                  <XCircle className="w-4 h-4 text-rose-600" />
                ) : (
                  <AlertTriangle className="w-4 h-4 text-amber-600" />
                )}
              </div>
              <div>
                <p className="font-semibold text-slate-900 leading-tight">
                  {title}
                </p>
                <p className="text-xs text-slate-600 mt-1 leading-normal">
                  {res.message}
                </p>

                {res.details && Object.keys(res.details).length > 0 && (
                  <div className="mt-2 text-xs font-mono bg-white/80 p-2 rounded border border-slate-200 text-slate-700">
                    {JSON.stringify(res.details, null, 2)}
                  </div>
                )}
              </div>
            </div>

            <span
              className={`text-[11px] font-semibold px-2 py-0.5 rounded uppercase flex-shrink-0 ${
                isPassed
                  ? 'bg-emerald-100 text-emerald-800'
                  : isCritical
                  ? 'bg-rose-100 text-rose-800'
                  : isError
                  ? 'bg-rose-100 text-rose-800'
                  : 'bg-amber-100 text-amber-800'
              }`}
            >
              {isPassed ? 'Passed' : res.severity}
            </span>
          </div>
        );
      })}
    </div>
  );
}
