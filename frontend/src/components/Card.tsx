import React from 'react';

export function Card({ title, children, className = '' }: { title?: string, children: React.ReactNode, className?: string }) {
  return (
    <div className={`bg-white border border-neutral-200 rounded-md shadow-sm overflow-hidden ${className}`}>
      {title && (
        <div className="px-4 py-3 border-b border-neutral-200 bg-neutral-50/50">
          <h3 className="text-sm font-semibold text-neutral-800">{title}</h3>
        </div>
      )}
      <div className="p-4">
        {children}
      </div>
    </div>
  );
}
