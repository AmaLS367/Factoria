import { useState, useEffect } from "react";
import { Card } from "./Card";
import type { SchemaTemplate } from "../types";
import { fetchTemplates, createTemplate, deleteTemplate } from "../api";
import {
  Plus,
  Trash2,
  Play,
  AlertCircle,
  X,
  LayoutTemplate,
} from "lucide-react";

interface TemplatesProps {
  onUseTemplate: (template: SchemaTemplate) => void;
}

export function Templates({ onUseTemplate }: TemplatesProps) {
  const [templates, setTemplates] = useState<SchemaTemplate[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Form state
  const [formName, setFormName] = useState("");
  const [formSlug, setFormSlug] = useState("");
  const [formDesc, setFormDesc] = useState("");
  const [formItemLabel, setFormItemLabel] = useState("");
  const [formColumnName, setFormColumnName] = useState("");
  const [formFields, setFormFields] = useState<string[]>([]);
  const [newFieldInput, setNewFieldInput] = useState("");
  const [formError, setFormError] = useState<string | null>(null);

  const loadTemplates = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await fetchTemplates();
      setTemplates(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadTemplates();
  }, []);

  const handleNameChange = (val: string) => {
    setFormName(val);
    if (!formSlug || formSlug === deriveSlug(formName)) {
      setFormSlug(deriveSlug(val));
    }
  };

  const deriveSlug = (name: string) => {
    return name
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "")
      .substring(0, 64);
  };

  const handleAddField = () => {
    const val = newFieldInput.trim();
    if (val && !formFields.includes(val)) {
      setFormFields([...formFields, val]);
    }
    setNewFieldInput("");
  };

  const handleRemoveField = (idx: number) => {
    setFormFields(formFields.filter((_, i) => i !== idx));
  };

  const handleSaveTemplate = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);

    if (
      !formName.trim() ||
      !formSlug.trim() ||
      !formItemLabel.trim() ||
      !formColumnName.trim()
    ) {
      setFormError("All main fields are required.");
      return;
    }
    if (formFields.length === 0) {
      setFormError("At least one target field is required.");
      return;
    }

    try {
      await createTemplate({
        name: formName.trim(),
        slug: formSlug.trim(),
        description: formDesc.trim(),
        item_label: formItemLabel.trim(),
        column_name: formColumnName.trim(),
        target_fields: formFields,
      });
      await loadTemplates();
      // Reset form
      setFormName("");
      setFormSlug("");
      setFormDesc("");
      setFormItemLabel("");
      setFormColumnName("");
      setFormFields([]);
    } catch (err) {
      setFormError(err instanceof Error ? err.message : String(err));
    }
  };

  const handleDeleteTemplate = async (slug: string) => {
    if (!confirm("Are you sure you want to delete this template?")) return;
    try {
      await deleteTemplate(slug);
      await loadTemplates();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      {/* Left Col: Template List */}
      <div className="lg:col-span-2 space-y-6">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-medium text-neutral-900 dark:text-neutral-100 flex items-center gap-2">
            <LayoutTemplate className="w-5 h-5 text-indigo-500" />
            Available Templates
          </h3>
        </div>

        {error && (
          <div className="p-3 bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-400 rounded text-sm border border-red-200 dark:border-red-800 flex items-center gap-2">
            <AlertCircle className="w-4 h-4" />
            {error}
          </div>
        )}

        {loading ? (
          <div className="p-8 text-center text-neutral-500">
            Loading templates...
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {templates.map((t) => (
              <div
                key={t.slug}
                className="bg-white dark:bg-neutral-900 border border-neutral-200 dark:border-neutral-700 rounded-lg shadow-sm flex flex-col"
              >
                <div className="p-4 flex-1">
                  <div className="flex justify-between items-start mb-2">
                    <div>
                      <h4 className="font-semibold text-neutral-900 dark:text-neutral-100 flex items-center gap-2">
                        {t.name}
                        {t.is_builtin && (
                          <span className="text-[10px] uppercase font-bold tracking-wider px-1.5 py-0.5 bg-neutral-100 dark:bg-neutral-800 text-neutral-500 rounded">
                            Built-in
                          </span>
                        )}
                      </h4>
                      <p className="text-xs text-neutral-500 mt-1 line-clamp-2">
                        {t.description}
                      </p>
                    </div>
                  </div>

                  <div className="mt-4 space-y-2 text-xs">
                    <div className="flex gap-2">
                      <span className="font-medium text-neutral-700 dark:text-neutral-300 w-20">
                        Item Label:
                      </span>
                      <span className="text-neutral-600 dark:text-neutral-400">
                        {t.item_label}
                      </span>
                    </div>
                    <div className="flex gap-2">
                      <span className="font-medium text-neutral-700 dark:text-neutral-300 w-20">
                        Column:
                      </span>
                      <span className="text-neutral-600 dark:text-neutral-400">
                        {t.column_name}
                      </span>
                    </div>
                  </div>

                  <div className="mt-4">
                    <p className="text-xs font-medium text-neutral-700 dark:text-neutral-300 mb-2">
                      Fields ({t.target_fields.length}):
                    </p>
                    <div className="flex flex-wrap gap-1.5">
                      {t.target_fields.map((f, i) => (
                        <span
                          key={i}
                          className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-medium bg-neutral-100 text-neutral-600 dark:bg-neutral-800 dark:text-neutral-300"
                        >
                          {f}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>

                <div className="p-3 border-t border-neutral-100 dark:border-neutral-800 bg-neutral-50 dark:bg-neutral-900/50 flex gap-2 justify-end rounded-b-lg">
                  {!t.is_builtin && (
                    <button
                      onClick={() => handleDeleteTemplate(t.slug)}
                      className="p-1.5 text-neutral-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 rounded transition-colors"
                      title="Delete template"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  )}
                  <button
                    onClick={() => onUseTemplate(t)}
                    className="inline-flex items-center px-3 py-1.5 border border-transparent text-xs font-medium rounded text-white bg-indigo-600 hover:bg-indigo-700 shadow-sm"
                  >
                    <Play className="w-3.5 h-3.5 mr-1.5 fill-current" />
                    Use in Excel Job
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Right Col: Create Form */}
      <div>
        <Card title="Create Template">
          <form onSubmit={handleSaveTemplate} className="space-y-4">
            {formError && (
              <div className="p-3 bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-400 rounded text-sm border border-red-200 dark:border-red-800">
                {formError}
              </div>
            )}

            <div>
              <label className="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1">
                Name
              </label>
              <input
                type="text"
                value={formName}
                onChange={(e) => handleNameChange(e.target.value)}
                className="w-full bg-white dark:bg-neutral-900 border border-neutral-300 dark:border-neutral-700 rounded-md px-3 py-2 text-sm text-neutral-900 dark:text-neutral-100"
                placeholder="e.g. My Custom Template"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1">
                Slug
              </label>
              <input
                type="text"
                value={formSlug}
                onChange={(e) =>
                  setFormSlug(
                    e.target.value.toLowerCase().replace(/[^a-z0-9-]+/g, ""),
                  )
                }
                className="w-full bg-white dark:bg-neutral-900 border border-neutral-300 dark:border-neutral-700 rounded-md px-3 py-2 text-sm text-neutral-500 font-mono"
                placeholder="my-custom-template"
              />
              <p className="mt-1 text-xs text-neutral-500">
                Must be unique. Existing custom templates will be overwritten.
              </p>
            </div>

            <div>
              <label className="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1">
                Description
              </label>
              <textarea
                value={formDesc}
                onChange={(e) => setFormDesc(e.target.value)}
                rows={2}
                className="w-full bg-white dark:bg-neutral-900 border border-neutral-300 dark:border-neutral-700 rounded-md px-3 py-2 text-sm text-neutral-900 dark:text-neutral-100"
                placeholder="Short summary of this template"
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1">
                  Item Label
                </label>
                <input
                  type="text"
                  value={formItemLabel}
                  onChange={(e) => setFormItemLabel(e.target.value)}
                  className="w-full bg-white dark:bg-neutral-900 border border-neutral-300 dark:border-neutral-700 rounded-md px-3 py-2 text-sm text-neutral-900 dark:text-neutral-100"
                  placeholder="e.g. product"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1">
                  ID Column Name
                </label>
                <input
                  type="text"
                  value={formColumnName}
                  onChange={(e) => setFormColumnName(e.target.value)}
                  className="w-full bg-white dark:bg-neutral-900 border border-neutral-300 dark:border-neutral-700 rounded-md px-3 py-2 text-sm text-neutral-900 dark:text-neutral-100"
                  placeholder="e.g. SKU"
                />
              </div>
            </div>

            <div className="pt-2 border-t border-neutral-200 dark:border-neutral-700">
              <label className="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-2">
                Target Fields
              </label>

              {formFields.length > 0 && (
                <div className="flex flex-wrap gap-2 mb-3">
                  {formFields.map((f, i) => (
                    <span
                      key={i}
                      className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium bg-indigo-50 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-800"
                    >
                      {f}
                      <button
                        type="button"
                        onClick={() => handleRemoveField(i)}
                        className="ml-1.5 text-indigo-500 hover:text-indigo-700 dark:hover:text-indigo-200 focus:outline-none"
                      >
                        <X className="w-3 h-3" />
                      </button>
                    </span>
                  ))}
                </div>
              )}

              <div className="flex gap-2">
                <input
                  type="text"
                  value={newFieldInput}
                  onChange={(e) => setNewFieldInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      e.preventDefault();
                      handleAddField();
                    }
                  }}
                  className="flex-1 bg-white dark:bg-neutral-900 border border-neutral-300 dark:border-neutral-700 rounded-md px-3 py-1.5 text-sm text-neutral-900 dark:text-neutral-100"
                  placeholder="e.g. Manufacturer"
                />
                <button
                  type="button"
                  onClick={handleAddField}
                  disabled={!newFieldInput.trim()}
                  className="inline-flex items-center px-3 py-1.5 border border-neutral-300 dark:border-neutral-600 rounded-md text-sm font-medium text-neutral-700 dark:text-neutral-300 bg-white dark:bg-neutral-800 hover:bg-neutral-50 dark:hover:bg-neutral-700 disabled:opacity-50"
                >
                  <Plus className="w-4 h-4" />
                </button>
              </div>
            </div>

            <div className="pt-4">
              <button
                type="submit"
                className="w-full inline-flex justify-center items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-neutral-900 hover:bg-neutral-800 dark:bg-white dark:text-neutral-900 dark:hover:bg-neutral-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-neutral-900"
              >
                Save Template
              </button>
            </div>
          </form>
        </Card>
      </div>
    </div>
  );
}
