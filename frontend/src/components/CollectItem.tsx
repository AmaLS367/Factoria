import { useState } from 'react';
import { collectItem } from '../api';
import { Card } from './Card';
import { DatabaseZap, Loader2 } from 'lucide-react';

export function CollectItem() {
  const [itemId, setItemId] = useState('');
  const [data, setData] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleCollect = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!itemId.trim()) return;

    setLoading(true);
    setError(null);
    try {
      const result = await collectItem(itemId);
      setData(result);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  };

  const renderValue = (val: unknown) => {
    if (val === null || val === undefined) return <span className="text-neutral-400 dark:text-neutral-500 italic">null</span>;
    if (typeof val === 'object') {
      if (Array.isArray(val)) {
        return (
          <ul className="list-disc pl-5 space-y-1">
            {val.map((item, i) => <li key={i}>{typeof item === 'object' ? JSON.stringify(item) : item}</li>)}
          </ul>
        );
      }
      return <pre className="text-xs bg-neutral-50 dark:bg-neutral-800 p-2 rounded overflow-auto max-h-40 border border-neutral-200 dark:border-neutral-700 dark:text-neutral-200">{JSON.stringify(val, null, 2)}</pre>;
    }
    return String(val);
  };

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      <Card title="Single Item Collection">
        <form onSubmit={handleCollect} className="flex space-x-3">
          <div className="flex-1">
            <input
              type="text"
              value={itemId}
              onChange={(e) => setItemId(e.target.value)}
              placeholder="Enter Item ID (e.g., entity name or identifier)..."
              className="block w-full px-3 py-2 border border-neutral-300 dark:border-neutral-600 rounded-md leading-5 bg-white dark:bg-neutral-800 dark:text-neutral-100 placeholder-neutral-500 dark:placeholder-neutral-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
              disabled={loading}
            />
          </div>
          <button
            type="submit"
            disabled={loading || !itemId.trim()}
            className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <DatabaseZap className="h-4 w-4 mr-2" />}
            Collect
          </button>
        </form>

        {error && (
          <div className="mt-4 p-3 bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-400 rounded-md text-sm border border-red-200 dark:border-red-800">
            {error}
          </div>
        )}
      </Card>

      {data && (
        <Card title="Collection Result">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-neutral-200 dark:divide-neutral-700 text-sm">
              <tbody className="divide-y divide-neutral-200 dark:divide-neutral-700 bg-white dark:bg-neutral-900">
                {Object.entries(data).map(([key, value]) => (
                  <tr key={key} className={key === 'Sources' ? 'bg-indigo-50/30 dark:bg-indigo-900/20' : ''}>
                    <td className="whitespace-nowrap py-3 pl-4 pr-3 font-medium text-neutral-900 dark:text-neutral-100 sm:pl-0 align-top w-1/4">
                      {key}
                    </td>
                    <td className="px-3 py-3 text-neutral-600 dark:text-neutral-300">
                      {renderValue(value)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </div>
  );
}
