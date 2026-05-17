import { useEffect, useState } from "react";
import { fetchItems, fetchItemSources, fetchItemFields } from "../api";
import type { ItemSource, ItemField } from "../types";
import { Card } from "./Card";
import { BarChart2, ChevronLeft, ChevronRight, Loader2, Link, X } from "lucide-react";

const PAGE_SIZE = 50;

function CredibilityBadge({ score }: { score: number | null }) {
  if (score === null) {
    return (
      <span className="inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium bg-neutral-100 text-neutral-500 dark:bg-neutral-700 dark:text-neutral-400">
        ?
      </span>
    );
  }
  if (score >= 0.7) {
    return (
      <span className="inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-400">
        High
      </span>
    );
  }
  if (score >= 0.45) {
    return (
      <span className="inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium bg-yellow-100 text-yellow-700 dark:bg-yellow-900/40 dark:text-yellow-400">
        Med
      </span>
    );
  }
  return (
    <span className="inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-400">
      Low
    </span>
  );
}

function SourcesPanel({
  identifierValue,
  onClose,
}: {
  identifierValue: string;
  onClose: () => void;
}) {
  const [sources, setSources] = useState<ItemSource[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchItemSources(identifierValue)
      .then(setSources)
      .catch((e: unknown) =>
        setError(e instanceof Error ? e.message : String(e)),
      )
      .finally(() => setLoading(false));
  }, [identifierValue]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40">
      <div className="bg-white dark:bg-neutral-900 rounded-lg shadow-xl w-full max-w-2xl max-h-[80vh] flex flex-col">
        <div className="flex items-center justify-between px-5 py-4 border-b border-neutral-200 dark:border-neutral-700">
          <h3 className="text-sm font-semibold text-neutral-800 dark:text-neutral-100">
            Sources —{" "}
            <span className="font-normal text-neutral-500">
              {identifierValue}
            </span>
          </h3>
          <button
            onClick={onClose}
            className="p-1 rounded hover:bg-neutral-100 dark:hover:bg-neutral-800 text-neutral-500"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
        <div className="overflow-y-auto flex-1 p-4">
          {loading && (
            <div className="flex justify-center py-8">
              <Loader2 className="w-5 h-5 animate-spin text-indigo-500" />
            </div>
          )}
          {error && <p className="text-red-600 text-sm">{error}</p>}
          {!loading && !error && sources.length === 0 && (
            <p className="text-neutral-500 dark:text-neutral-400 text-sm text-center py-8">
              No sources found.
            </p>
          )}
          {!loading &&
            sources.map((src, i) => (
              <div
                key={i}
                className="mb-3 p-3 rounded border border-neutral-200 dark:border-neutral-700 bg-neutral-50 dark:bg-neutral-800"
              >
                <div className="flex items-start justify-between gap-2">
                  <a
                    href={src.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-indigo-600 dark:text-indigo-400 text-sm font-medium hover:underline truncate flex-1"
                  >
                    {src.title || src.url}
                  </a>
                  <CredibilityBadge score={src.credibility_score} />
                </div>
                {src.title && (
                  <p className="text-xs text-neutral-500 dark:text-neutral-400 truncate mt-0.5">
                    {src.url}
                  </p>
                )}
                {src.snippet && (
                  <p className="text-xs text-neutral-600 dark:text-neutral-300 mt-1 line-clamp-2">
                    {src.snippet}
                  </p>
                )}
                <div className="flex gap-2 mt-1.5 text-xs text-neutral-400">
                  {src.provider && src.provider !== "legacy" && (
                    <span className="px-1.5 py-0.5 rounded bg-neutral-200 dark:bg-neutral-700">
                      {src.provider}
                    </span>
                  )}
                  {src.credibility_score !== null && (
                    <span>score: {src.credibility_score.toFixed(2)}</span>
                  )}
                </div>
              </div>
            ))}
        </div>
      </div>
    </div>
  );
}

function FieldsPanel({
  identifierValue,
  onClose,
}: {
  identifierValue: string;
  onClose: () => void;
}) {
  const [fields, setFields] = useState<ItemField[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchItemFields(identifierValue)
      .then(setFields)
      .catch((e: unknown) =>
        setError(e instanceof Error ? e.message : String(e)),
      )
      .finally(() => setLoading(false));
  }, [identifierValue]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40">
      <div className="bg-white dark:bg-neutral-900 rounded-lg shadow-xl w-full max-w-2xl max-h-[80vh] flex flex-col">
        <div className="flex items-center justify-between px-5 py-4 border-b border-neutral-200 dark:border-neutral-700">
          <h3 className="text-sm font-semibold text-neutral-800 dark:text-neutral-100">
            Field Confidence —{" "}
            <span className="font-normal text-neutral-500">
              {identifierValue}
            </span>
          </h3>
          <button
            onClick={onClose}
            className="p-1 rounded hover:bg-neutral-100 dark:hover:bg-neutral-800 text-neutral-500"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
        <div className="overflow-y-auto flex-1 p-4">
          {loading && (
            <div className="flex justify-center py-8">
              <Loader2 className="w-5 h-5 animate-spin text-indigo-500" />
            </div>
          )}
          {error && <p className="text-red-600 text-sm">{error}</p>}
          {!loading && !error && fields.length === 0 && (
            <p className="text-neutral-500 dark:text-neutral-400 text-sm text-center py-8">
              No fields found.
            </p>
          )}
          {!loading && fields.length > 0 && (
            <table className="min-w-full divide-y divide-neutral-200 dark:divide-neutral-700">
              <thead className="bg-neutral-50 dark:bg-neutral-800">
                <tr>
                  <th
                    scope="col"
                    className="px-4 py-2 text-left text-xs font-semibold text-neutral-500 w-1/3"
                  >
                    Field
                  </th>
                  <th
                    scope="col"
                    className="px-4 py-2 text-left text-xs font-semibold text-neutral-500 w-1/3"
                  >
                    Value
                  </th>
                  <th
                    scope="col"
                    className="px-4 py-2 text-right text-xs font-semibold text-neutral-500 w-1/3"
                  >
                    Confidence
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white dark:bg-neutral-900 divide-y divide-neutral-200 dark:divide-neutral-700">
                {fields.map((f, i) => (
                  <tr
                    key={i}
                    className="hover:bg-neutral-50 dark:hover:bg-neutral-800"
                  >
                    <td className="px-4 py-2 text-sm text-neutral-500">
                      {f.field_name}
                    </td>
                    <td
                      className="px-4 py-2 text-sm text-neutral-800 dark:text-neutral-200 truncate max-w-xs"
                      title={f.field_value}
                    >
                      {f.field_value}
                    </td>
                    <td className="px-4 py-2 text-right">
                      <CredibilityBadge score={f.confidence} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}

export function ItemsTable() {
  const [items, setItems] = useState<Record<string, unknown>[]>([]);
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [openSourcesFor, setOpenSourcesFor] = useState<string | null>(null);
  const [openFieldsFor, setOpenFieldsFor] = useState<string | null>(null);

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
    return () => {
      mounted = false;
    };
  }, [offset]);

  const columns =
    items.length > 0
      ? Object.keys(items[0]).filter((c) => c !== "Sources")
      : [];
  const hasIdentifier = items.length > 0;

  if (error) {
    return (
      <Card>
        <div className="p-4 text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20 rounded border border-red-200 dark:border-red-800">
          Failed to load items: {error}
        </div>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      {openSourcesFor && (
        <SourcesPanel
          identifierValue={openSourcesFor}
          onClose={() => setOpenSourcesFor(null)}
        />
      )}
      {openFieldsFor && (
        <FieldsPanel
          identifierValue={openFieldsFor}
          onClose={() => setOpenFieldsFor(null)}
        />
      )}

      <Card className="flex flex-col">
        <div className="flex justify-between items-center px-4 py-3 border-b border-neutral-200 dark:border-neutral-700 bg-neutral-50/50 dark:bg-neutral-800/50">
          <h3 className="text-sm font-semibold text-neutral-800 dark:text-neutral-100">
            Database Records
          </h3>
          <div className="flex items-center space-x-2">
            {loading && (
              <Loader2 className="w-4 h-4 text-neutral-400 dark:text-neutral-500 animate-spin mr-2" />
            )}
            <span className="text-xs text-neutral-500 dark:text-neutral-400">
              Showing {offset + 1} – {offset + items.length}
            </span>
            <div className="flex space-x-1 ml-4">
              <button
                onClick={() => setOffset(offset - PAGE_SIZE)}
                disabled={offset === 0 || loading}
                className="p-1 rounded text-neutral-500 dark:text-neutral-400 hover:bg-neutral-200 dark:hover:bg-neutral-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <ChevronLeft className="w-5 h-5" />
              </button>
              <button
                onClick={() => setOffset(offset + PAGE_SIZE)}
                disabled={items.length < PAGE_SIZE || loading}
                className="p-1 rounded text-neutral-500 dark:text-neutral-400 hover:bg-neutral-200 dark:hover:bg-neutral-700 disabled:opacity-50 disabled:cursor-not-allowed"
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
                  {hasIdentifier && (
                    <th
                      scope="col"
                      className="px-4 py-3 text-left text-xs font-semibold text-neutral-600 dark:text-neutral-300 uppercase tracking-wider"
                    >
                      Actions
                    </th>
                  )}
                </tr>
              </thead>
              <tbody className="bg-white dark:bg-neutral-900 divide-y divide-neutral-200 dark:divide-neutral-700 text-sm">
                {items.map((row, i) => {
                  const firstVal =
                    columns.length > 0 ? String(row[columns[0]] ?? "") : "";
                  return (
                    <tr
                      key={i}
                      className="hover:bg-indigo-50/30 dark:hover:bg-indigo-900/20 transition-colors"
                    >
                      {columns.map((col) => {
                        const val = row[col];
                        let displayVal = String(val);
                        if (val === null || val === undefined) displayVal = "-";
                        else if (typeof val === "object")
                          displayVal = JSON.stringify(val);
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
                      {hasIdentifier && (
                        <td className="px-4 py-2">
                          <div className="flex gap-2">
                            <button
                              onClick={() => {
                                setOpenSourcesFor(firstVal);
                                setOpenFieldsFor(null);
                              }}
                              className="inline-flex items-center gap-1 px-2 py-1 text-xs text-indigo-600 dark:text-indigo-400 hover:bg-indigo-50 dark:hover:bg-indigo-900/30 rounded transition-colors"
                            >
                              <Link className="w-3 h-3" />
                              Sources
                            </button>
                            <button
                              onClick={() => {
                                setOpenFieldsFor(firstVal);
                                setOpenSourcesFor(null);
                              }}
                              className="inline-flex items-center gap-1 px-2 py-1 text-xs text-neutral-600 dark:text-neutral-300 hover:bg-neutral-100 dark:hover:bg-neutral-800 rounded transition-colors"
                            >
                              <BarChart2 className="w-3 h-3" />
                              Details
                            </button>
                          </div>
                        </td>
                      )}
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>
      </Card>
    </div>
  );
}
