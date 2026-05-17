import { useEffect, useRef, useState } from 'react';
import { fetchLogs } from '../api';
import type { LogEntry } from '../types';
import { Card } from './Card';
import { RefreshCw, Loader2 } from 'lucide-react';

type Level = 'ALL' | 'INFO' | 'WARNING' | 'ERROR' | 'DEBUG';

const LEVEL_STYLES: Record<string, string> = {
  INFO:    'border-green-400 bg-green-50 dark:bg-green-900/10',
  WARNING: 'border-yellow-400 bg-yellow-50 dark:bg-yellow-900/10',
  ERROR:   'border-red-400 bg-red-50 dark:bg-red-900/10',
  DEBUG:   'border-neutral-300 bg-neutral-50 dark:bg-neutral-800',
};

const LEVEL_BADGE: Record<string, string> = {
  INFO:    'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-400',
  WARNING: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/40 dark:text-yellow-400',
  ERROR:   'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-400',
  DEBUG:   'bg-neutral-100 text-neutral-600 dark:bg-neutral-700 dark:text-neutral-400',
};

export function Logs() {
  const [entries, setEntries] = useState<LogEntry[]>([]);
  const [level, setLevel] = useState<Level>('ALL');
  const [autoRefresh, setAutoRefresh] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const intervalRef = useRef<number | null>(null);

  const load = async (filterLevel: Level = level) => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchLogs(300, filterLevel === 'ALL' ? '' : filterLevel);
      setEntries([...data.entries].reverse());
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  useEffect(() => {
    if (intervalRef.current) clearInterval(intervalRef.current);
    if (autoRefresh) {
      intervalRef.current = window.setInterval(() => load(), 5000);
    }
    return () => { if (intervalRef.current) clearInterval(intervalRef.current); };
  }, [autoRefresh, level]);

  const handleLevel = (l: Level) => {
    setLevel(l);
    load(l);
  };

  const LEVELS: Level[] = ['ALL', 'INFO', 'WARNING', 'ERROR', 'DEBUG'];

  return (
    <div className="max-w-5xl mx-auto space-y-4">
      <Card>
        <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
          <div className="flex gap-1">
            {LEVELS.map(l => (
              <button key={l} onClick={() => handleLevel(l)}
                className={`px-3 py-1 text-xs font-medium rounded transition-colors ${
                  level === l
                    ? 'bg-indigo-600 text-white'
                    : 'bg-neutral-100 dark:bg-neutral-800 text-neutral-600 dark:text-neutral-300 hover:bg-neutral-200 dark:hover:bg-neutral-700'
                }`}>
                {l}
              </button>
            ))}
          </div>
          <div className="flex items-center gap-3">
            <label className="flex items-center gap-1.5 text-xs text-neutral-600 dark:text-neutral-300 cursor-pointer">
              <input type="checkbox" checked={autoRefresh} onChange={e => setAutoRefresh(e.target.checked)}
                className="accent-indigo-600" />
              Auto-refresh (5s)
            </label>
            <button onClick={() => load()}
              className="inline-flex items-center gap-1 px-3 py-1.5 text-xs font-medium rounded border border-neutral-300 dark:border-neutral-600 text-neutral-600 dark:text-neutral-300 hover:bg-neutral-100 dark:hover:bg-neutral-800 transition-colors">
              {loading ? <Loader2 className="w-3 h-3 animate-spin" /> : <RefreshCw className="w-3 h-3" />}
              Refresh
            </button>
          </div>
        </div>

        {error && (
          <div className="mb-3 p-3 bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-400 rounded text-sm border border-red-200 dark:border-red-800">
            {error}
          </div>
        )}

        {!loading && entries.length === 0 && !error && (
          <div className="flex items-center justify-center h-48 text-neutral-400 dark:text-neutral-500 text-sm">
            No log entries yet.
          </div>
        )}

        <div className="space-y-1 font-mono text-xs">
          {entries.map((entry, i) => {
            const borderBg = LEVEL_STYLES[entry.level] ?? LEVEL_STYLES.DEBUG;
            const badge = LEVEL_BADGE[entry.level] ?? LEVEL_BADGE.DEBUG;
            return (
              <div key={i} className={`flex gap-2 items-start border-l-2 pl-3 py-1 rounded-r ${borderBg}`}>
                <span className="text-neutral-400 dark:text-neutral-500 shrink-0 hidden sm:inline">
                  {entry.timestamp}
                </span>
                <span className={`px-1.5 py-0.5 rounded text-xs font-semibold shrink-0 ${badge}`}>
                  {entry.level}
                </span>
                <span className="text-neutral-500 dark:text-neutral-400 shrink-0 hidden md:inline">
                  {entry.logger}
                </span>
                <span className="text-neutral-800 dark:text-neutral-200 break-all">{entry.message}</span>
              </div>
            );
          })}
        </div>
      </Card>
    </div>
  );
}
