import { AlertTriangle, X } from 'lucide-react';
import type { ConfirmationModalProps } from '../types' 

export default function ConfirmationModal({
  isOpen,
  title = 'Delete Space',
  message,
  confirmLabel = 'Delete',
  cancelLabel = 'Cancel',
  isLoading = false,
  onConfirm,
  onCancel,
}: ConfirmationModalProps) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fadeIn">
      {/* Click outside to close */}
      <div className="fixed inset-0" onClick={onCancel} />

      <div className="relative w-full max-w-md p-6 bg-white dark:bg-gray-900 rounded-2xl shadow-2xl border border-gray-100 dark:border-gray-800 z-10 transition-all">
        {/* Close Button */}
        <button
          onClick={onCancel}
          className="absolute top-4 right-4 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 transition-colors"
        >
          <X size={18} />
        </button>

        <div className="flex items-start gap-4">
          <div className="p-3 bg-red-100 dark:bg-red-950/50 rounded-xl text-red-600 dark:text-red-400">
            <AlertTriangle size={24} />
          </div>

          <div className="flex-1">
            <h3 className="text-lg font-bold text-gray-900 dark:text-gray-100">
              {title}
            </h3>
            <p className="mt-1 text-sm text-gray-500 dark:text-gray-400 leading-relaxed">
              {message}
            </p>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="mt-6 flex justify-end gap-3">
          <button
            type="button"
            disabled={isLoading}
            onClick={onCancel}
            className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 rounded-xl transition-colors disabled:opacity-50"
          >
            {cancelLabel}
          </button>
          <button
            type="button"
            disabled={isLoading}
            onClick={onConfirm}
            className="px-4 py-2 text-sm font-medium text-white bg-red-600 hover:bg-red-700 rounded-xl transition-colors disabled:opacity-50 flex items-center gap-2 shadow-sm"
          >
            {isLoading ? 'Deleting...' : confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}