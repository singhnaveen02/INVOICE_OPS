import React from 'react';
import {
  FileText,
  Scan,
  Database,
  Building2,
  FileCheck2,
  CopyX,
  Calculator,
  ShieldCheck,
  Scale,
  Save,
  CheckCircle2,
  Clock,
  AlertTriangle,
  XCircle,
  Loader2,
} from 'lucide-react';
import { formatDuration } from '../utils/format';

const STAGE_CONFIG = [
  { key: 'document_received', name: 'Document Received', icon: FileText },
  { key: 'pdf_parsing', name: 'PDF Parsing / OCR', icon: Scan },
  { key: 'field_extraction', name: 'Field Extraction', icon: FileCheck2 },
  { key: 'vendor_identification', name: 'Vendor Identification', icon: Building2 },
  { key: 'po_matching', name: 'PO Matching Engine', icon: Database },
  { key: 'duplicate_detection', name: 'Duplicate Detection', icon: CopyX },
  { key: 'financial_reconciliation', name: 'Financial Reconciliation', icon: Calculator },
  { key: 'business_validation', name: 'Business Rules Validation', icon: ShieldCheck },
  { key: 'decision_generation', name: 'Decision Engine', icon: Scale },
  { key: 'database_persistence', name: 'Database Persistence', icon: Save },
];

export default function ProcessingTimeline({ stages = [] }) {
  // Map stages by stage_name
  const stageMap = {};
  stages.forEach((s) => {
    stageMap[s.stage_name] = s;
  });

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
      <div className="flex items-center justify-between mb-6 pb-3 border-b border-slate-100">
        <div>
          <h3 className="text-base font-semibold text-slate-900">Live Processing View</h3>
          <p className="text-xs text-slate-500 mt-0.5">
            10-Stage Deterministic Accounts Payable Pipeline
          </p>
        </div>
        <span className="text-xs font-mono bg-slate-100 text-slate-600 px-2 py-1 rounded">
          {stages.filter((s) => s.status === 'COMPLETED').length} / 10 Complete
        </span>
      </div>

      <div className="space-y-4 relative">
        {/* Connecting line */}
        <div className="absolute left-4 top-4 bottom-4 w-0.5 bg-slate-100 -z-0" />

        {STAGE_CONFIG.map((conf, index) => {
          const stage = stageMap[conf.key];
          const isCompleted = stage?.status === 'COMPLETED';
          const isFailed = stage?.status === 'FAILED';
          const isWarning = stage?.status === 'WARNING';
          const isRunning = stage?.status === 'RUNNING';
          const isPending = !stage;

          const IconComponent = conf.icon;

          return (
            <div key={conf.key} className="flex items-start gap-4 relative z-10">
              {/* Step indicator node */}
              <div
                className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 text-xs font-semibold transition-colors ${
                  isCompleted
                    ? 'bg-emerald-100 text-emerald-700 ring-2 ring-emerald-400'
                    : isFailed
                    ? 'bg-rose-100 text-rose-700 ring-2 ring-rose-400'
                    : isWarning
                    ? 'bg-amber-100 text-amber-700 ring-2 ring-amber-400'
                    : isRunning
                    ? 'bg-sky-100 text-sky-700 ring-2 ring-sky-400 animate-pulse'
                    : 'bg-slate-100 text-slate-400'
                }`}
              >
                {isCompleted ? (
                  <CheckCircle2 className="w-4 h-4" />
                ) : isFailed ? (
                  <XCircle className="w-4 h-4" />
                ) : isWarning ? (
                  <AlertTriangle className="w-4 h-4" />
                ) : isRunning ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <span>{index + 1}</span>
                )}
              </div>

              {/* Step details */}
              <div className="flex-1 bg-slate-50/70 rounded-lg p-3 border border-slate-100">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <IconComponent className="w-4 h-4 text-slate-500" />
                    <span className="text-sm font-semibold text-slate-800">
                      {conf.name}
                    </span>
                  </div>
                  {stage?.duration_ms !== undefined && stage?.duration_ms !== null && (
                    <span className="text-xs font-mono text-slate-500">
                      {formatDuration(stage.duration_ms)}
                    </span>
                  )}
                </div>

                {/* Findings summary if available */}
                {stage?.findings && Object.keys(stage.findings).length > 0 && (
                  <div className="mt-2 text-xs text-slate-600 bg-white p-2 rounded border border-slate-100 font-mono flex flex-wrap gap-x-4 gap-y-1">
                    {Object.entries(stage.findings).map(([k, v]) => (
                      <span key={k}>
                        <strong className="text-slate-500">{k}:</strong>{' '}
                        <span className="text-slate-800">{String(v)}</span>
                      </span>
                    ))}
                  </div>
                )}

                {/* Error message */}
                {stage?.error_message && (
                  <p className="mt-1.5 text-xs text-rose-600 bg-rose-50 p-2 rounded border border-rose-100">
                    {stage.error_message}
                  </p>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
