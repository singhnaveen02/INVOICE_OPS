import React from 'react';
import { FileQuestion } from 'lucide-react';

export default function EmptyState({
  title = 'No records found',
  description = 'Try adjusting your search or filters.',
  action = null,
  icon: Icon = FileQuestion,
}) {
  return (
    <div className="flex flex-col items-center justify-center py-16 px-4 text-center bg-white rounded-xl border border-dashed border-slate-200">
      <div className="w-12 h-12 rounded-full bg-slate-50 flex items-center justify-center text-slate-400 mb-3">
        <Icon className="w-6 h-6" />
      </div>
      <h3 className="text-sm font-semibold text-slate-900">{title}</h3>
      <p className="text-xs text-slate-500 max-w-sm mt-1 mb-4">{description}</p>
      {action}
    </div>
  );
}
