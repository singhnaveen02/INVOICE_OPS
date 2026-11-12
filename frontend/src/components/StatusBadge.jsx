import React from 'react';
import { CheckCircle2, AlertTriangle, XCircle, Clock, RefreshCw } from 'lucide-react';

export default function StatusBadge({ status, size = 'md' }) {
  const norm = (status || '').toUpperCase();

  const configs = {
    APPROVE: {
      bg: 'bg-emerald-50 text-emerald-700 border-emerald-200',
      icon: CheckCircle2,
      label: 'APPROVED',
    },
    APPROVED: {
      bg: 'bg-emerald-50 text-emerald-700 border-emerald-200',
      icon: CheckCircle2,
      label: 'APPROVED',
    },
    REVIEW: {
      bg: 'bg-amber-50 text-amber-700 border-amber-200',
      icon: AlertTriangle,
      label: 'NEEDS REVIEW',
    },
    REJECT: {
      bg: 'bg-rose-50 text-rose-700 border-rose-200',
      icon: XCircle,
      label: 'REJECTED',
    },
    REJECTED: {
      bg: 'bg-rose-50 text-rose-700 border-rose-200',
      icon: XCircle,
      label: 'REJECTED',
    },
    PROCESSING: {
      bg: 'bg-sky-50 text-sky-700 border-sky-200',
      icon: RefreshCw,
      label: 'PROCESSING',
      spin: true,
    },
    PENDING: {
      bg: 'bg-slate-50 text-slate-700 border-slate-200',
      icon: Clock,
      label: 'PENDING',
    },
  };

  const current = configs[norm] || configs.PENDING;
  const Icon = current.icon;

  const sizeClasses = {
    sm: 'text-xs px-2 py-0.5 gap-1',
    md: 'text-xs px-2.5 py-1 gap-1.5',
    lg: 'text-sm px-3.5 py-1.5 gap-2 font-semibold',
  }[size] || 'text-xs px-2.5 py-1 gap-1.5';

  return (
    <span
      className={`inline-flex items-center font-medium rounded-full border ${current.bg} ${sizeClasses}`}
    >
      <Icon className={`w-3.5 h-3.5 ${current.spin ? 'animate-spin' : ''}`} />
      <span>{current.label}</span>
    </span>
  );
}
