import { useEffect, useState } from 'react';
import { fetchItems } from '../api';
import { Card } from './Card';
import { ChevronLeft, ChevronRight, Loader2 } from 'lucide-react';

const PAGE_SIZE = 50;

export function ItemsTable() {
  const [items, setItems] = useState<Record<string, unknown>[]>([]);
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;

    async function load() {
      setLoading(true);
      setError(null);
      try {
        const data = await fetchItems(PAGE_SIZE, offset);
        if (mounted) setItems(data);
      } catch (err: unknown) {
        if (mounted) setError(err instanceof Error ? err.message : String(err));
      } finally {
        if (mounted) setLoading(false);
      }
    }

    load();
    return () => { mounted = false; };
  }, [offset]);

  const handlePrev = () => {
    if (offset >= PAGE_SIZE) {
      setOffset(offset - PAGE_SIZE);
    }
  };

  const handleNext = () => {
    if (items.length === PAGE_SIZE) {
      setOffset(offset + PAGE_SIZE);
    }
  };

  if (error) {
    return (
      <Card>
        <div className="p-4 text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20 rounded border border-red-200 dark:border-red-800">
          Failed to load items: {error}
        </div>
      </Card>
    );
  }

  const columns = items.length > 0 ? Object.keys(items[0]) : [];

  return (
    <div className="space-y-4">
      <Card className="flex flex-col">
        <div className="flex justify-between items-center px-4 py-3 border-b border-neutral-200 dark:border-neutral-700 bg-neutral-50/50 dark:bg-neutral-800/50">
          <h3 className="text-sm font-semibold text-neutral-800 dark:text-neutral-100">Database Records</h3>
          <div className="flex items-center space-x-2">
            {loading && <Loader2 className="w-4 h-4 text-neutral-400 dark:text-neutral-500 animate-spin mr-2" />}
            <span className="text-xs text-neutral-500 dark:text-neutral-400">
              Showing {offset + 1} - {offset + items.length}
            </span>
            <div className="flex space-x-1 ml-4">
              <button
                onClick={handlePrev}
                disabled={offset === 0 || loading}
                className="p-1 rounded text-neutral-500 dark:text-neutral-400 hover:bg-neutral-200 dark:hover:bg-neutral-700 disabled:opacity-50 disabled:cursor-not-allowed"
                title="Previous Page"
              >
                <ChevronLeft className="w-5 h-5" />
              </button>
              <button
                onClick={handleNext}
                disabled={items.length < PAGE_SIZE || loading}
                className="p-1 rounded text-neutral-500 dark:text-neutral-400 hover:bg-neutral-200 dark:hover:bg-neutral-700 disabled:opacity-50 disabled:cursor-not-allowed"
                title="Next Page"
              >
                <ChevronRight className="w-5 h-5" />
              </button>
            </div>
          </div>
        </div>

        <div className="overflow-x-auto min-h-[300px]">
          {items.length === 0 && !loading ? (
            <div className="flex items-center justify-center h-48 text-neutral-500 dark:text-neutral-400 text-sm">
              No records found.
            </div>
          ) : (
            <table className="min-w-full divide-y divide-neutral-200 dark:divide-neutral-700">
              <thead className="bg-neutral-50 dark:bg-neutral-800">
                <tr>
                  {columns.map((col) => (
                    <th
                      key={col}
                      scope="col"
                      className="px-4 py-3 text-left text-xs font-semibold text-neutral-600 dark:text-neutral-300 uppercase tracking-wider whitespace-nowrap"
                    >
                      {col}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="bg-white dark:bg-neutral-900 divide-y divide-neutral-200 dark:divide-neutral-700 text-sm">
                {items.map((row, i) => (
                  <tr key={i} className="hover:bg-indigo-50/30 dark:hover:bg-indigo-900/20 transition-colors">
                    {columns.map((col) => {
                      const val = row[col];
                      let displayVal = String(val);
                      if (val === null || val === undefined) displayVal = '-';
                      else if (typeof val === 'object') displayVal = JSON.stringify(val);

                      return (
                        <td
                          key={col}
                          className="px-4 py-2 text-neutral-700 dark:text-neutral-300 whitespace-nowrap max-w-xs overflow-hidden text-ellipsis"
                          title={displayVal}
                        >
                          {displayVal}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </Card>
    </div>
  );
}
