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
    await createNewSpace(selectedTool, spaceName);
    
    // Reset local state after successful creation 
    // (The modal is automatically closed by the Zustand store logic)
    setSpaceName('');
    setSelectedTool('summary');
    setIsSubmitting(false);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
      <div className="bg-white rounded-xl shadow-lg w-full max-w-md p-6 relative">
        <button 
          onClick={() => setNewSpaceModalOpen(false)}
          className="absolute top-4 right-4 text-gray-400 hover:text-gray-600 transition-colors"
          disabled={isSubmitting}
        >
          <X size={20} />
        </button>
        
        <h2 className="text-xl font-semibold mb-4 text-gray-800">Create New Space</h2>
        
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Select Tool
            </label>
            <select 
              value={selectedTool}
              onChange={(e) => setSelectedTool(e.target.value as 'summary' | 'research')}
              className="w-full border border-gray-300 rounded-lg p-2.5 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none bg-white"
              disabled={isSubmitting}
            >
              <option value="summary">Summary Agent</option>
              <option value="research">Research Agent</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Space Name
            </label>
            <input 
              type="text"
              value={spaceName}
              onChange={(e) => setSpaceName(e.target.value)}
              placeholder="e.g., Quantum Physics"
              className="w-full border border-gray-300 rounded-lg p-2.5 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
              autoFocus
              required
              disabled={isSubmitting}
            />
          </div>

          <div className="flex justify-end gap-3 mt-6">
            <button
              type="button"
              onClick={() => setNewSpaceModalOpen(false)}
              className="px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
              disabled={isSubmitting}
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={!spaceName.trim() || isSubmitting}
              className="px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center min-w-[120px]"
            >
              {isSubmitting ? 'Creating...' : 'Create Space'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}