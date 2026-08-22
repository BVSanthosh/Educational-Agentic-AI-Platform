import { useState } from 'react';
import { useAppStore } from '../store/useAppStore';
import { X } from 'lucide-react';
 
export default function NewSpaceModal() {
  const { isNewSpaceModalOpen, setNewSpaceModalOpen, createNewSpace } = useAppStore();
  
  // Local state for the form
  const [spaceName, setSpaceName] = useState('');
  const [selectedTool, setSelectedTool] = useState<'summary' | 'research'>('summary');
  const [isSubmitting, setIsSubmitting] = useState(false);

  // If the modal isn't open, render nothing
  if (!isNewSpaceModalOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!spaceName.trim()) return;
    
    setIsSubmitting(true);
    // Call the async store function (hits your FastAPI backend)
    const uploadStatus: 'chat' | 'upload' = selectedTool === "summary" ? "upload" : "chat"
    await createNewSpace(selectedTool, spaceName, uploadStatus);
    
    // Reset local state after successful creation 
    // (The modal is automatically closed by the Zustand store logic)
    setSpaceName('');
    setSelectedTool('summary');
    setIsSubmitting(false);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 dark:bg-black/70 backdrop-blur-sm transition-colors duration-200">
      <div className="bg-white dark:bg-gray-900 border border-transparent dark:border-gray-800 rounded-xl shadow-lg w-full max-w-md p-6 relative transition-colors duration-200">
        <button 
          onClick={() => setNewSpaceModalOpen(false)}
          className="absolute top-4 right-4 text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
          disabled={isSubmitting}
        >
          <X size={20} />
        </button>
        
        <h2 className="text-xl font-semibold mb-4 text-gray-800 dark:text-gray-100 transition-colors">Create New Space</h2>
        
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1 transition-colors">
              Select Tool
            </label>
            <select 
              value={selectedTool}
              onChange={(e) => setSelectedTool(e.target.value as 'summary' | 'research')}
              className="w-full border border-gray-300 dark:border-gray-700 rounded-lg p-2.5 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 transition-colors"
              disabled={isSubmitting}
            >
              <option value="summary">Summary Agent</option>
              <option value="research">Research Agent</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1 transition-colors">
              Space Name
            </label>
            <input 
              type="text"
              value={spaceName}
              onChange={(e) => setSpaceName(e.target.value)}
              placeholder="e.g., Quantum Physics"
              className="w-full border border-gray-300 dark:border-gray-700 rounded-lg p-2.5 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 placeholder-gray-400 dark:placeholder-gray-500 transition-colors"
              autoFocus
              required
              disabled={isSubmitting}
            />
          </div>

          <div className="flex justify-end gap-3 mt-6">
            <button
              type="button"
              onClick={() => setNewSpaceModalOpen(false)}
              className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
              disabled={isSubmitting}
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={!spaceName.trim() || isSubmitting}
              className="px-4 py-2 text-sm font-medium text-white bg-blue-600 dark:bg-blue-500 hover:bg-blue-700 dark:hover:bg-blue-600 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center min-w-[120px]"
            >
              {isSubmitting ? 'Creating...' : 'Create Space'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}