import { useState } from 'react';
import { runExcelJob, getExportUrl } from '../api';
import type { ExcelJobStatus } from '../types';
import { Card } from './Card';
import { FileSpreadsheet, Play, Download, Loader2 } from 'lucide-react';

export function ExcelJob() {
  const [status, setStatus] = useState<ExcelJobStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleRunJob = async () => {
    setLoading(true);
    setError(null);
    setStatus(null);
    try {
      const data = await runExcelJob();
      setStatus(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6 max-w-2xl mx-auto">
      <Card title="Batch Excel Job">
        <div className="space-y-4">
          <p className="text-sm text-neutral-600">
            Run a batch job to process all items in the configured input file.
            This will use the research agent to collect data and write the results to an Excel export.
          </p>

          <div className="flex space-x-3">
            <button
              onClick={handleRunJob}
              disabled={loading}
              className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Play className="h-4 w-4 mr-2 fill-current" />}
              {loading ? 'Processing...' : 'Run Excel Job'}
            </button>

            <a
              href={getExportUrl()}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center px-4 py-2 border border-neutral-300 shadow-sm text-sm font-medium rounded-md text-neutral-700 bg-white hover:bg-neutral-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
            >
              <Download className="h-4 w-4 mr-2" />
              Download Latest Export
            </a>
          </div>
        </div>

        {error && (
          <div className="mt-4 p-3 bg-red-50 text-red-700 rounded-md text-sm border border-red-200">
            {error}
          </div>
        )}

        {status && (
          <div className="mt-4 p-4 bg-green-50 border border-green-200 rounded-md">
            <div className="flex items-center mb-2">
              <FileSpreadsheet className="w-5 h-5 text-green-600 mr-2" />
              <h4 className="font-medium text-green-800">Job Completed Successfully</h4>
            </div>
            <p className="text-sm text-green-700">
              Output saved to: <code className="bg-white/50 px-1 py-0.5 rounded ml-1">{status.output_path}</code>
            </p>
          </div>
        )}
      </Card>
    </div>
  );
}
