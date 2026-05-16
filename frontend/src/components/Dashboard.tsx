import { useEffect, useState } from 'react';
import { fetchHealth, fetchSettings } from '../api';
import type { HealthStatus, Settings } from '../types';
import { Card } from './Card';
import { Activity, Database, CheckCircle2, XCircle } from 'lucide-react';

const StatusIcon = ({ status }: { status: string }) => {
  return status === 'ok' ? (
    <CheckCircle2 className="w-5 h-5 text-green-600" />
  ) : (
    <XCircle className="w-5 h-5 text-red-600" />
  );
};

export function Dashboard() {
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [settings, setSettings] = useState<Settings | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const [h, s] = await Promise.all([fetchHealth(), fetchSettings()]);
        setHealth(h);
        setSettings(s);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error occurred');
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  if (loading) return <div className="p-4 text-neutral-500">Loading dashboard...</div>;
  if (error) return <div className="p-4 text-red-600 bg-red-50 rounded border border-red-200">Error: {error}</div>;

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card title="System Health">
          <div className="space-y-4">
            <div className="flex items-center justify-between p-3 bg-neutral-50 rounded border border-neutral-200">
              <div className="flex items-center space-x-3">
                <Activity className="w-5 h-5 text-neutral-500" />
                <span className="font-medium text-neutral-700">API Status</span>
              </div>
              <div className="flex items-center space-x-2">
                <StatusIcon status={health?.status || 'unknown'} />
                <span className="text-sm text-neutral-600 capitalize">{health?.status}</span>
              </div>
            </div>
            <div className="flex items-center justify-between p-3 bg-neutral-50 rounded border border-neutral-200">
              <div className="flex items-center space-x-3">
                <Database className="w-5 h-5 text-neutral-500" />
                <span className="font-medium text-neutral-700">Database</span>
              </div>
              <div className="flex items-center space-x-2">
                <StatusIcon status={health?.db || 'unknown'} />
                <span className="text-sm text-neutral-600 capitalize">{health?.db}</span>
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
              <div key={i} className="flex flex-col sm:flex-row sm:justify-between py-2 border-b border-neutral-100 last:border-0">
                <span className="text-sm text-neutral-500">{item.label}</span>
                <span className="text-sm font-medium text-neutral-800 break-all">{item.value?.toString() || '—'}</span>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </div>
  );
}
