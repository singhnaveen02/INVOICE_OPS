export const formatCurrency = (amount, currency = 'USD') => {
  if (amount === null || amount === undefined) return '—';
  try {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: currency || 'USD',
    }).format(amount);
  } catch {
    return `$${Number(amount).toFixed(2)}`;
  }
};

export const formatDate = (dateStr) => {
  if (!dateStr) return '—';
  try {
    const d = new Date(dateStr);
    if (isNaN(d.getTime())) return dateStr;
    return d.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  } catch {
    return dateStr;
  }
};

export const formatPercent = (val) => {
  if (val === null || val === undefined) return '—';
  return `${Number(val).toFixed(1)}%`;
};

export const formatDuration = (ms) => {
  if (!ms && ms !== 0) return '—';
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(2)}s`;
};
