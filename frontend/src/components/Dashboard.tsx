import { useEffect, useState } from 'react';
import { fetchHealth, fetchSettings } from '../api';
import type { HealthStatus, Settings } from '../types';
import { Card } from './Card';
import { Activity, Database, CheckCircle2, XCircle } from 'lucide-react';

const StatusIcon = ({ status }: { status: string }) => {
  return status === 'ok' ? (
    <CheckCircle2 className="w-5 h-5 text-green-600 dark:text-green-400" />
  ) : (
    <XCircle className="w-5 h-5 text-red-600 dark:text-red-400" />
  );
};

export function Dashboard() {
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [settings, setSettings] = useState<Settings | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    async function load() {
      try {
        const [h, s] = await Promise.all([fetchHealth(), fetchSettings()]);
        if (mounted) {
          setHealth(h);
          setSettings(s);
        }
      } catch (err) {
        if (mounted) {
          setError(err instanceof Error ? err.message : 'Unknown error occurred');
        }
      } finally {
        if (mounted) {
          setLoading(false);
        }
      }
    }
    load();
    return () => {
      mounted = false;
    };
  }, []);

  if (loading) return <div className="p-4 text-neutral-500 dark:text-neutral-400">Loading dashboard...</div>;
  if (error) return <div className="p-4 text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20 rounded border border-red-200 dark:border-red-800">Error: {error}</div>;

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card title="System Health">
          <div className="space-y-4">
            <div className="flex items-center justify-between p-3 bg-neutral-50 dark:bg-neutral-800 rounded border border-neutral-200 dark:border-neutral-700">
              <div className="flex items-center space-x-3">
                <Activity className="w-5 h-5 text-neutral-500 dark:text-neutral-400" />
                <span className="font-medium text-neutral-700 dark:text-neutral-200">API Status</span>
              </div>
              <div className="flex items-center space-x-2">
                <StatusIcon status={health?.status || 'unknown'} />
                <span className="text-sm text-neutral-600 dark:text-neutral-300 capitalize">{health?.status}</span>
              </div>
            </div>
            <div className="flex items-center justify-between p-3 bg-neutral-50 dark:bg-neutral-800 rounded border border-neutral-200 dark:border-neutral-700">
              <div className="flex items-center space-x-3">
                <Database className="w-5 h-5 text-neutral-500 dark:text-neutral-400" />
                <span className="font-medium text-neutral-700 dark:text-neutral-200">Database</span>
              </div>
              <div className="flex items-center space-x-2">
                <StatusIcon status={health?.db || 'unknown'} />
                <span className="text-sm text-neutral-600 dark:text-neutral-300 capitalize">{health?.db}</span>
              </div>
            </div>
          </div>
        </Card>

        <Card title="Current Configuration">
          <div className="space-y-3">
            {[
              { label: 'Model Name', value: settings?.model_name },
              { label: 'Provider', value: settings?.llm_provider },
              { label: 'LLM Model', value: settings?.llm_model },
              { label: 'Web Search', value: settings?.web_search_enabled ? 'Enabled' : 'Disabled' },
              { label: 'Input File', value: settings?.input_file },
              { label: 'Output File', value: settings?.output_file },
            ].map((item, i) => (
              <div key={i} className="flex flex-col sm:flex-row sm:justify-between py-2 border-b border-neutral-100 dark:border-neutral-700 last:border-0">
                <span className="text-sm text-neutral-500 dark:text-neutral-400">{item.label}</span>
                <span className="text-sm font-medium text-neutral-800 dark:text-neutral-100 break-all">{item.value?.toString() || '—'}</span>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </div>
  );
}
