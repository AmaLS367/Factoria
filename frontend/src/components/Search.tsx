import { useState } from 'react';
import { searchWeb } from '../api';
import type { SearchResult } from '../types';
import { Card } from './Card';
import { Search as SearchIcon, ExternalLink, Loader2 } from 'lucide-react';
import { isSafeUrl } from '../utils/url';

export function Search() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hasSearched, setHasSearched] = useState(false);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;

    setLoading(true);
    setError(null);
    try {
      const data = await searchWeb(query);
      setResults(data);
      setHasSearched(true);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      <Card title="Web Search Tool">
        <form onSubmit={handleSearch} className="flex space-x-3">
          <div className="relative flex-1">
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
              <SearchIcon className="h-5 w-5 text-neutral-400 dark:text-neutral-500" />
            </div>
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Enter search query..."
              className="block w-full pl-10 pr-3 py-2 border border-neutral-300 dark:border-neutral-600 rounded-md leading-5 bg-white dark:bg-neutral-800 dark:text-neutral-100 placeholder-neutral-500 dark:placeholder-neutral-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
              disabled={loading}
            />
          </div>
          <button
            type="submit"
            disabled={loading || !query.trim()}
            className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : null}
            Search
          </button>
        </form>

        {error && (
          <div className="mt-4 p-3 bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-400 rounded-md text-sm border border-red-200 dark:border-red-800">
            {error}
          </div>
        )}
      </Card>

      {hasSearched && (
        <div className="space-y-4">
          <h3 className="text-lg font-medium text-neutral-800 dark:text-neutral-100">
            Search Results ({results.length})
          </h3>
          {results.length === 0 && !loading ? (
            <div className="text-neutral-500 dark:text-neutral-400 p-4 text-center bg-white dark:bg-neutral-900 border border-neutral-200 dark:border-neutral-700 rounded-md">
              No results found for "{query}".
            </div>
          ) : (
            <div className="space-y-4">
              {results.map((result, i) => {
                const safeUrl = isSafeUrl(result.url) ? result.url : undefined;
                return (
                  <Card key={i}>
                    <div className="flex flex-col space-y-2">
                      {safeUrl ? (
                        <a
                          href={safeUrl}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-indigo-600 dark:text-indigo-400 hover:text-indigo-800 dark:hover:text-indigo-300 font-medium text-lg flex items-start"
                        >
                          {result.title}
                          <ExternalLink className="w-4 h-4 ml-2 flex-shrink-0 mt-1" />
                        </a>
                      ) : (
                        <span className="text-neutral-800 dark:text-neutral-100 font-medium text-lg flex items-start">
                          {result.title}
                        </span>
                      )}
                      <div className="text-xs text-neutral-500 dark:text-neutral-400 truncate">{result.url}</div>
                      <p className="text-sm text-neutral-700 dark:text-neutral-300 leading-relaxed">{result.snippet}</p>
                    </div>
                  </Card>
                );
              })}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
