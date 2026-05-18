import { useEffect, useState, useCallback } from 'react';
import { listReviewFields, reviewField, fetchReviewSummary } from '../api';
import type { ReviewField } from '../types';
import { Card } from './Card';
import {
  Check,
  X,
  Edit2,
  AlertTriangle,
  Award,
  RefreshCw,
  FileText,
  CheckSquare,
  MessageSquare
} from 'lucide-react';

export function ReviewPage() {
  const [fields, setFields] = useState<ReviewField[]>([]);
  const [summary, setSummary] = useState<Record<string, number>>({});
  const [statusFilter, setStatusFilter] = useState<string>('needs_review');
  const [jobIdFilter, setJobIdFilter] = useState<string>('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Pagination
  const [limit] = useState(50);
  const [offset, setOffset] = useState(0);
  const [hasMore, setHasMore] = useState(true);

  // Edit / Correction State
  const [editingFieldId, setEditingFieldId] = useState<number | null>(null);
  const [correctedValue, setCorrectedValue] = useState<string>('');
  const [reviewerNote, setReviewerNote] = useState<string>('');
  const [submittingId, setSubmittingId] = useState<number | null>(null);

  const loadData = useCallback(async (reset: boolean = false) => {
    setLoading(true);
    setError(null);
    try {
      const currentOffset = reset ? 0 : offset;
      if (reset) {
        setOffset(0);
      }

      const [fieldsData, summaryData] = await Promise.all([
        listReviewFields(statusFilter, limit, currentOffset, jobIdFilter || undefined),
        fetchReviewSummary(jobIdFilter || undefined)
      ]);

      if (reset) {
        setFields(fieldsData);
      } else {
        setFields((prev) => [...prev, ...fieldsData]);
      }

      setSummary(summaryData);
      setHasMore(fieldsData.length === limit);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch review data');
    } finally {
      setLoading(false);
    }
  }, [statusFilter, jobIdFilter, limit, offset]);

  // Load on filter change
  useEffect(() => {
    loadData(true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [statusFilter, jobIdFilter]);

  const handleLoadMore = () => {
    const nextOffset = offset + limit;
    setOffset(nextOffset);
    // We want loadData to fetch with the next offset without clearing existing data
    setLoading(true);
    listReviewFields(statusFilter, limit, nextOffset, jobIdFilter || undefined)
      .then((fieldsData) => {
        setFields((prev) => [...prev, ...fieldsData]);
        setHasMore(fieldsData.length === limit);
        setOffset(nextOffset);
      })
      .catch((err) => {
        setError(err instanceof Error ? err.message : 'Failed to fetch more review data');
      })
      .finally(() => {
        setLoading(false);
      });
  };

  const handleDecision = async (
    fieldId: number,
    decision: 'approved' | 'rejected',
    val?: string,
    note?: string
  ) => {
    setSubmittingId(fieldId);
    try {
      const updated = await reviewField(fieldId, decision, val, note);
      // Remove from current list if it no longer matches status filter, or update inline
      if (statusFilter === 'needs_review' || statusFilter !== updated.review_status) {
        setFields((prev) => prev.filter((f) => f.field_id !== fieldId));
      } else {
        setFields((prev) => prev.map((f) => (f.field_id === fieldId ? updated : f)));
      }
      // Refresh summary stats
      const summaryData = await fetchReviewSummary(jobIdFilter || undefined);
      setSummary(summaryData);
      // Reset edit state
      setEditingFieldId(null);
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Error updating field decision');
    } finally {
      setSubmittingId(null);
    }
  };

  const startEdit = (field: ReviewField) => {
    setEditingFieldId(field.field_id);
    setCorrectedValue(field.field_value || '');
    setReviewerNote(field.reviewer_note || '');
  };

  const cancelEdit = () => {
    setEditingFieldId(null);
    setCorrectedValue('');
    setReviewerNote('');
  };

  const saveCorrection = async (fieldId: number) => {
    if (!correctedValue.trim()) {
      alert('Value cannot be empty for corrected status');
      return;
    }
    setSubmittingId(fieldId);
    try {
      const updated = await reviewField(fieldId, 'corrected', correctedValue, reviewerNote || undefined);
      if (statusFilter === 'needs_review' || statusFilter !== updated.review_status) {
        setFields((prev) => prev.filter((f) => f.field_id !== fieldId));
      } else {
        setFields((prev) => prev.map((f) => (f.field_id === fieldId ? updated : f)));
      }
      const summaryData = await fetchReviewSummary(jobIdFilter || undefined);
      setSummary(summaryData);
      cancelEdit();
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Error saving correction');
    } finally {
      setSubmittingId(null);
    }
  };

  const getConfidenceBadge = (confidence: number | null) => {
    if (confidence === null) return null;
    const percentage = Math.round(confidence * 100);
    let colorClass = 'bg-red-50 text-red-700 dark:bg-red-900/20 dark:text-red-400 border-red-200 dark:border-red-800';
    let label = 'Low';

    if (confidence >= 0.85) {
      colorClass = 'bg-green-50 text-green-700 dark:bg-green-900/20 dark:text-green-400 border-green-200 dark:border-green-800';
      label = 'High';
    } else if (confidence >= 0.5) {
      colorClass = 'bg-yellow-50 text-yellow-700 dark:bg-yellow-900/20 dark:text-yellow-400 border-yellow-200 dark:border-yellow-800';
      label = 'Medium';
    }

    return (
      <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold border ${colorClass}`}>
        {percentage}% ({label})
      </span>
    );
  };

  const getStatusBadge = (status: string) => {
    let classes = 'bg-neutral-100 text-neutral-800 border-neutral-300';
    if (status === 'approved') classes = 'bg-green-100 text-green-800 border-green-300 dark:bg-green-900/30 dark:text-green-300 dark:border-green-800';
    if (status === 'corrected') classes = 'bg-blue-100 text-blue-800 border-blue-300 dark:bg-blue-900/30 dark:text-blue-300 dark:border-blue-800';
    if (status === 'rejected') classes = 'bg-red-100 text-red-800 border-red-300 dark:bg-red-900/30 dark:text-red-300 dark:border-red-800';
    if (status === 'needs_review') classes = 'bg-yellow-100 text-yellow-800 border-yellow-300 dark:bg-yellow-900/30 dark:text-yellow-300 dark:border-yellow-800';
    if (status === 'auto_accepted') classes = 'bg-purple-100 text-purple-800 border-purple-300 dark:bg-purple-900/30 dark:text-purple-300 dark:border-purple-800';

    return (
      <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-bold border capitalize ${classes}`}>
        {status.replace('_', ' ')}
      </span>
    );
  };

  return (
    <div className="space-y-6">
      {/* Summary Stats Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-4">
        {[
          { label: 'Needs Review', val: summary.needs_review ?? 0, icon: AlertTriangle, color: 'text-yellow-600 bg-yellow-50 dark:bg-yellow-900/20' },
          { label: 'Auto Accepted', val: summary.auto_accepted ?? 0, icon: Award, color: 'text-purple-600 bg-purple-50 dark:bg-purple-900/20' },
          { label: 'Approved', val: summary.approved ?? 0, icon: CheckSquare, color: 'text-green-600 bg-green-50 dark:bg-green-900/20' },
          { label: 'Corrected', val: summary.corrected ?? 0, icon: Edit2, color: 'text-blue-600 bg-blue-50 dark:bg-blue-900/20' },
          { label: 'Rejected', val: summary.rejected ?? 0, icon: X, color: 'text-red-600 bg-red-50 dark:bg-red-900/20' },
        ].map((item, idx) => {
          const Icon = item.icon;
          return (
            <Card key={idx} className="!p-0">
              <div className="p-4 flex items-center justify-between">
                <div>
                  <p className="text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wider">{item.label}</p>
                  <p className="text-2xl font-bold mt-1 text-neutral-900 dark:text-white">{item.val}</p>
                </div>
                <div className={`p-2 rounded ${item.color}`}>
                  <Icon className="w-5 h-5" />
                </div>
              </div>
            </Card>
          );
        })}
      </div>

      {/* Filter and Control Bar */}
      <div className="flex flex-col sm:flex-row gap-4 items-stretch justify-between p-4 bg-white dark:bg-neutral-900 border border-neutral-200 dark:border-neutral-700 rounded-md shadow-sm">
        <div className="flex flex-col sm:flex-row items-center gap-4 flex-1">
          <div className="w-full sm:w-48">
            <label className="block text-xs font-medium text-neutral-500 dark:text-neutral-400 mb-1">Review Status</label>
            <div className="relative">
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="w-full pl-3 pr-10 py-1.5 bg-neutral-50 dark:bg-neutral-800 border border-neutral-300 dark:border-neutral-600 rounded text-sm text-neutral-800 dark:text-neutral-100 focus:outline-none focus:ring-1 focus:ring-blue-500"
              >
                <option value="needs_review">Needs Review</option>
                <option value="auto_accepted">Auto Accepted</option>
                <option value="approved">Approved</option>
                <option value="corrected">Corrected</option>
                <option value="rejected">Rejected</option>
              </select>
            </div>
          </div>

          <div className="w-full sm:w-64">
            <label className="block text-xs font-medium text-neutral-500 dark:text-neutral-400 mb-1">Filter by Job ID</label>
            <div className="relative flex items-center">
              <input
                type="text"
                value={jobIdFilter}
                onChange={(e) => setJobIdFilter(e.target.value)}
                placeholder="All jobs"
                className="w-full pl-3 pr-8 py-1.5 bg-neutral-50 dark:bg-neutral-800 border border-neutral-300 dark:border-neutral-600 rounded text-sm text-neutral-800 dark:text-neutral-100 focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
              {jobIdFilter && (
                <button
                  onClick={() => setJobIdFilter('')}
                  className="absolute right-2 text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-200"
                >
                  <X className="w-4 h-4" />
                </button>
              )}
            </div>
          </div>
        </div>

        <div className="flex items-end justify-end">
          <button
            onClick={() => loadData(true)}
            className="flex items-center justify-center space-x-2 px-4 py-2 border border-neutral-300 dark:border-neutral-600 rounded text-sm font-medium text-neutral-700 dark:text-neutral-200 hover:bg-neutral-50 dark:hover:bg-neutral-800 transition"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* Main Content Area */}
      {error && (
        <div className="p-4 text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20 rounded border border-red-200 dark:border-red-800">
          Error: {error}
        </div>
      )}

      <Card title={`Review Queue — ${fields.length} Fields Shown`}>
        {fields.length === 0 && !loading ? (
          <div className="p-12 text-center text-neutral-500 dark:text-neutral-400">
            <CheckSquare className="w-12 h-12 mx-auto text-neutral-300 dark:text-neutral-700 mb-4 animate-bounce" />
            <p className="text-lg font-semibold">No review items found</p>
            <p className="text-sm mt-1">Fields matching this filter are empty. Excellent job!</p>
          </div>
        ) : (
          <div className="divide-y divide-neutral-200 dark:divide-neutral-800 -mx-4 -my-4">
            {fields.map((field) => {
              const isEditing = editingFieldId === field.field_id;
              const isSubmitting = submittingId === field.field_id;

              return (
                <div key={field.field_id} className="p-4 hover:bg-neutral-50/50 dark:hover:bg-neutral-800/10 transition">
                  <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-4">
                    {/* Left: Identifier Details */}
                    <div className="space-y-1.5 flex-1">
                      <div className="flex items-center space-x-2 flex-wrap gap-y-1">
                        <span className="text-xs font-semibold text-neutral-400 uppercase tracking-wide">
                          {field.identifier_column}
                        </span>
                        <span className="text-sm font-bold text-neutral-800 dark:text-white bg-neutral-100 dark:bg-neutral-800 px-2 py-0.5 rounded">
                          {field.identifier_value}
                        </span>
                        {getConfidenceBadge(field.confidence)}
                        {getStatusBadge(field.review_status)}
                      </div>

                      <div className="flex items-center space-x-2">
                        <span className="text-xs font-medium text-neutral-500 dark:text-neutral-400">Field:</span>
                        <span className="text-sm font-bold text-blue-600 dark:text-blue-400">{field.field_name}</span>
                      </div>

                      {field.job_id && (
                        <div className="text-xs text-neutral-400 flex items-center space-x-1">
                          <FileText className="w-3.5 h-3.5" />
                          <span>Job ID: {field.job_id}</span>
                        </div>
                      )}

                      {/* Display existing reviewer note if present */}
                      {field.reviewer_note && (
                        <div className="mt-2 text-xs text-neutral-600 dark:text-neutral-300 bg-neutral-50 dark:bg-neutral-800/50 border border-neutral-200 dark:border-neutral-700/50 rounded p-2 flex items-start space-x-1.5 max-w-xl">
                          <MessageSquare className="w-3.5 h-3.5 mt-0.5 text-neutral-400 flex-shrink-0" />
                          <div>
                            <span className="font-semibold text-neutral-700 dark:text-neutral-200">Reviewer Note: </span>
                            <span>{field.reviewer_note}</span>
                          </div>
                        </div>
                      )}
                    </div>

                    {/* Middle: Extracted/Corrected Values */}
                    <div className="flex-1 md:max-w-md">
                      {!isEditing ? (
                        <div className="bg-neutral-50 dark:bg-neutral-800/40 rounded border border-neutral-200 dark:border-neutral-800 p-3">
                          <span className="block text-xs font-medium text-neutral-400 mb-1">Extracted Value</span>
                          <span className="text-sm font-semibold text-neutral-800 dark:text-neutral-100 break-words">
                            {field.field_value === null ? <em className="text-neutral-400">None</em> : field.field_value}
                          </span>
                        </div>
                      ) : (
                        <div className="space-y-3 bg-blue-50/30 dark:bg-blue-900/10 border border-blue-200 dark:border-blue-900/50 rounded-md p-3">
                          <div>
                            <label className="block text-xs font-semibold text-blue-700 dark:text-blue-300 mb-1">Corrected Value</label>
                            <input
                              type="text"
                              value={correctedValue}
                              onChange={(e) => setCorrectedValue(e.target.value)}
                              disabled={isSubmitting}
                              placeholder="Enter corrected value"
                              className="w-full px-2.5 py-1.5 bg-white dark:bg-neutral-900 border border-blue-300 dark:border-blue-800 rounded text-sm text-neutral-800 dark:text-neutral-100 focus:outline-none focus:ring-1 focus:ring-blue-500"
                            />
                          </div>

                          <div>
                            <label className="block text-xs font-semibold text-blue-700 dark:text-blue-300 mb-1">Reviewer Note (Optional)</label>
                            <textarea
                              value={reviewerNote}
                              onChange={(e) => setReviewerNote(e.target.value)}
                              disabled={isSubmitting}
                              placeholder="Explain correction (e.g. fixed unit, updated spelling)"
                              rows={2}
                              className="w-full px-2.5 py-1.5 bg-white dark:bg-neutral-900 border border-blue-300 dark:border-blue-800 rounded text-xs text-neutral-800 dark:text-neutral-100 focus:outline-none focus:ring-1 focus:ring-blue-500 resize-none"
                            />
                          </div>

                          <div className="flex space-x-2">
                            <button
                              onClick={() => saveCorrection(field.field_id)}
                              disabled={isSubmitting}
                              className="px-3 py-1 bg-blue-600 hover:bg-blue-700 text-white rounded text-xs font-semibold flex items-center space-x-1 transition disabled:opacity-50"
                            >
                              <Check className="w-3.5 h-3.5" />
                              <span>Save</span>
                            </button>
                            <button
                              onClick={cancelEdit}
                              disabled={isSubmitting}
                              className="px-3 py-1 border border-neutral-300 dark:border-neutral-700 hover:bg-neutral-100 dark:hover:bg-neutral-800 text-neutral-700 dark:text-neutral-300 rounded text-xs font-medium transition disabled:opacity-50"
                            >
                              Cancel
                            </button>
                          </div>
                        </div>
                      )}
                    </div>

                    {/* Right: Actions */}
                    {!isEditing && (
                      <div className="flex md:flex-col justify-end items-center md:items-end gap-2 mt-2 md:mt-0 flex-shrink-0">
                        {field.review_status === 'needs_review' ? (
                          <>
                            <button
                              onClick={() => handleDecision(field.field_id, 'approved')}
                              disabled={isSubmitting}
                              className="w-full md:w-32 justify-center px-3 py-1.5 bg-green-600 hover:bg-green-700 text-white rounded text-xs font-bold flex items-center space-x-1.5 transition disabled:opacity-50"
                            >
                              <Check className="w-3.5 h-3.5" />
                              <span>Approve</span>
                            </button>

                            <button
                              onClick={() => startEdit(field)}
                              disabled={isSubmitting}
                              className="w-full md:w-32 justify-center px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded text-xs font-bold flex items-center space-x-1.5 transition disabled:opacity-50"
                            >
                              <Edit2 className="w-3.5 h-3.5" />
                              <span>Correct</span>
                            </button>

                            <button
                              onClick={() => handleDecision(field.field_id, 'rejected')}
                              disabled={isSubmitting}
                              className="w-full md:w-32 justify-center px-3 py-1.5 bg-red-600 hover:bg-red-700 text-white rounded text-xs font-bold flex items-center space-x-1.5 transition disabled:opacity-50"
                            >
                              <X className="w-3.5 h-3.5" />
                              <span>Reject</span>
                            </button>
                          </>
                        ) : (
                          // Allow re-reviewing already processed entries
                          <button
                            onClick={() => {
                              // Reset review status to needs_review to let them edit/change decisions
                              // To do this, we can call reviewField with 'needs_review' or directly trigger edit
                              startEdit(field);
                            }}
                            className="w-full md:w-32 justify-center px-3 py-1.5 border border-neutral-300 dark:border-neutral-700 hover:bg-neutral-100 dark:hover:bg-neutral-800 text-neutral-700 dark:text-neutral-300 rounded text-xs font-semibold flex items-center space-x-1.5 transition"
                          >
                            <Edit2 className="w-3.5 h-3.5" />
                            <span>Modify Decision</span>
                          </button>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {/* Load More Button */}
        {hasMore && !loading && fields.length > 0 && (
          <div className="mt-6 text-center border-t border-neutral-200 dark:border-neutral-800 pt-4">
            <button
              onClick={handleLoadMore}
              className="px-6 py-2 border border-neutral-300 dark:border-neutral-600 rounded text-sm font-semibold text-neutral-700 dark:text-neutral-200 hover:bg-neutral-50 dark:hover:bg-neutral-800 transition"
            >
              Load More Items
            </button>
          </div>
        )}

        {loading && fields.length > 0 && (
          <div className="text-center py-4 text-sm text-neutral-500">
            Loading next page...
          </div>
        )}
      </Card>
    </div>
  );
}
