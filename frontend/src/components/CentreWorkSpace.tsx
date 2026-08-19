import { useState, useEffect } from 'react';
import { useAppStore } from '../store/useAppStore';
import { UploadCloud, Send, Bot, FileText, ArrowRight, User, BookOpen, ExternalLink } from 'lucide-react';
import type { Message } from '../types'; 

export default function CentreWorkspace() {
  const { 
    activeTool, 
    activeSessionId, 
    sessions, 
    updateSessionState, 
    addMessage, 
    updateStreamingMessage, 
    token, 
    ensureReferenceSpaceExists,
    loadSpaceData, 
    activeChat, 
    activeReferences,
    setAgentProgress,
    setActiveDocument

  } = useAppStore();

  console.log("ACTIVE CHAT: ", activeChat)

  const [inputValue, setInputValue] = useState('');
  const [isUploading, setIsUploading] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);

  // Determine the active session for conditional UI rendering (upload vs chat views)
  const activeSession = activeTool !== 'reference' && activeSessionId
    ? sessions[activeTool].find(s => s.id === activeSessionId)
    : null;

  // --- AUTO-FETCH HISTORY HOOK ---
  useEffect(() => {
    const fetchContextData = async () => {
      if (activeTool === 'reference') {
        const spaceId = await ensureReferenceSpaceExists();
        if (spaceId) await loadSpaceData(spaceId, 'reference');
      } else if (activeSessionId) {
        await loadSpaceData(activeSessionId, activeTool);
      }
    };
    
    fetchContextData();
  }, [activeTool, activeSessionId, loadSpaceData, ensureReferenceSpaceExists]);

  // --- MOCK ACTION HANDLERS ---
  const handleSimulateUpload = () => {
    if (!activeSession) return;
    setIsUploading(true);
    console.log("Sending file to backend");
    setTimeout(() => {
      setIsUploading(false);
      updateSessionState(activeTool as 'summary' | 'research', activeSession.id, 'chat');
    }, 1500);
  };

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputValue.trim() || isProcessing) return;

    const query = inputValue;
    setInputValue('');
    setIsProcessing(true);

    try {
      // -------------------------------------------------------------
      // CASE A: Reference Generation Tool
      // -------------------------------------------------------------
      if (activeTool === 'reference') {
        const spaceId = await ensureReferenceSpaceExists();
        if (!spaceId) throw new Error("Could not initialize the reference space.");

        const res = await fetch(`http://localhost:8000/api/references/${spaceId}`, {
          method: 'POST',
          headers: { 
            'Content-Type': 'application/json', 
            ...(token ? { 'Authorization': `Bearer ${token}` } : {})
          },
          credentials: 'include',
          body: JSON.stringify({ user_input: query }) 
        });

        if (!res.ok) throw new Error('Failed to generate references');
        
        // Re-fetch data to update activeReferences centrally in the store
        await loadSpaceData(spaceId, 'reference');
        setIsProcessing(false);
      }
      
      // -------------------------------------------------------------
      // CASE B: Summary & Research Tools (Streaming Chat)
      // -------------------------------------------------------------
      else if (activeSession) {
        const spaceId = activeSession.id;

        // 1. Add User Message
        const userMessage: Message = {
          id: crypto.randomUUID(),
          role: 'user',
          content: query,
        };
        addMessage(userMessage); 

        const agentMessageId = crypto.randomUUID();
        
        // 2. DONT add the empty agent message yet! 
        // Instead, instantly trigger the progress banner so the user knows it's thinking.
        setAgentProgress("Analyzing request...");
        setIsProcessing(false); // Turn off the input spinner, we are using the progress banner now.

        const response = await fetch(`http://localhost:8000/api/${activeTool}/${spaceId}/stream`, {
          method: 'POST',
          headers: { 
            'Content-Type': 'application/json', 
            ...(token ? { 'Authorization': `Bearer ${token}` } : {})
          },
          credentials: 'include',
          body: JSON.stringify({ user_input: query })
        });

        if (!response.ok || !response.body) {
          throw new Error('Failed to stream response from backend');
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        let accumulatedText = '';
        
        // 3. Track whether we have created the bubble yet
        let agentMessageAdded = false; 

        while (true) {
          const { value, done } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const events = buffer.split('\n\n');
          buffer = events.pop() || ''; 

          for (const event of events) {
            if (event.startsWith('data: ')) {
              try {
                const dataStr = event.slice(6);
                const payload = JSON.parse(dataStr);

                if (payload.type === 'progress') {
                  setAgentProgress(payload.message);
                } 
                else if (payload.type === 'token') {
                  // 4. The moment the first token arrives, create the bubble and hide the progress!
                  if (!agentMessageAdded) {
                    addMessage({
                      id: agentMessageId,
                      role: 'agent',
                      content: '',
                    });
                    agentMessageAdded = true;
                    setAgentProgress(null); 
                  }

                  accumulatedText += payload.content;
                  updateStreamingMessage(agentMessageId, accumulatedText);
                } 
                else if (payload.type === 'document_ready') {
                  setActiveDocument(payload.document_id);
                }
                else if (payload.type === 'error') {
                  console.error("Agent Error:", payload.message);
                  setAgentProgress(`Error: ${payload.message}`);
                }
                else if (payload.type === 'done') {
                  setAgentProgress(null);
                }
              } catch {
                console.warn("Failed to parse SSE JSON:", event);
              }
            }
          }
        }
      }
    } catch (error) {
      console.error("API request error:", error);
      setIsProcessing(false);
      useAppStore.getState().setAgentProgress(null);
    }
  };

  // --- VIEW 1: Empty State ---
  if (activeTool !== 'reference' && !activeSessionId) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center text-center p-6 bg-gray-50/50">
        <div className="w-16 h-16 bg-blue-100 text-blue-600 rounded-2xl flex items-center justify-center mb-4">
          <FileText size={32} />
        </div>
        <h3 className="text-xl font-semibold text-gray-800 mb-2">No Space Selected</h3>
        <p className="text-gray-500 max-w-sm">
          Please select an existing {activeTool} space from the sidebar, or create a new one to get started.
        </p>
      </div>
    );
  }

  // --- VIEW 2: File Upload State ---
  if (activeSession?.state === 'upload') {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-6">
        <div className="max-w-md w-full">
          <div className="text-center mb-6">
            <h3 className="text-2xl font-bold text-gray-800">Upload your Document</h3>
            <p className="text-gray-500 mt-2">Initialize your {activeTool} space with a source file.</p>
          </div>
          
          <button 
            onClick={handleSimulateUpload}
            disabled={isUploading}
            className="w-full border-2 border-dashed border-gray-300 rounded-2xl p-12 flex flex-col items-center justify-center bg-gray-50 hover:bg-gray-100 hover:border-blue-400 transition-all group disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <div className="w-16 h-16 bg-white shadow-sm rounded-full flex items-center justify-center mb-4 group-hover:scale-105 transition-transform">
              <UploadCloud size={32} className="text-blue-500" />
            </div>
            <p className="font-medium text-gray-700">
              {isUploading ? 'Uploading & Processing...' : 'Click or drag file to upload'}
            </p>
            <p className="text-sm text-gray-400 mt-2">Supports PDF, DOCX, or TXT</p>
          </button>
        </div>
      </div>
    );
  }

  const currentMessages = activeChat?.messages || [];

  // --- VIEW 3: Chat Interface (Reference Tool or Active Chat Session) ---
  return (
    <div className="flex-1 flex flex-col min-h-0 relative">
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        
        {/* REFERENCE TOOL VIEW */}
        {activeTool === 'reference' ? (
          <div className="max-w-3xl mx-auto space-y-6 w-full">
            <div className="bg-blue-50 border border-blue-100 p-6 rounded-2xl flex items-start gap-4">
              <div className="w-10 h-10 rounded-xl bg-blue-600 flex items-center justify-center text-white shrink-0">
                <BookOpen size={20} />
              </div>
              <div>
                <h3 className="font-semibold text-blue-900 text-lg">Reference Generator</h3>
                <p className="text-blue-700 text-sm mt-1">
                  Enter any academic topic or keyword below to compile formal references and citations.
                </p>
              </div>
            </div>

            {activeReferences && (
              <div className="space-y-6">
                {/* Description Box */}
                {activeReferences.description && (
                  <div className="bg-white border border-gray-200 p-5 rounded-2xl shadow-sm text-gray-700">
                    <h4 className="font-semibold text-gray-900 mb-1 text-sm uppercase tracking-wider text-blue-600">Overview</h4>
                    <p className="text-sm leading-relaxed">{activeReferences.description}</p>
                  </div>
                )}

                {/* References List */}
                {activeReferences.references && activeReferences.references.length > 0 && (
                  <div className="space-y-4">
                    <h4 className="font-semibold text-gray-800 text-lg">
                      Generated Resources ({activeReferences.references.length})
                    </h4>
                    {activeReferences.references.map((ref, index) => (
                      <div key={index} className="bg-white border border-gray-200 p-5 rounded-xl shadow-sm flex items-center justify-between gap-4 group hover:border-blue-300 transition-colors">
                        <div className="space-y-1 min-w-0">
                          <span className="text-xs font-bold text-blue-600 bg-blue-50 px-2.5 py-0.5 rounded-full">
                            Ref [{index + 1}]
                          </span>
                          <h5 className="font-semibold text-gray-900 text-base truncate">{ref.title}</h5>
                          <a 
                            href={ref.url} 
                            target="_blank" 
                            rel="noopener noreferrer" 
                            className="text-xs text-blue-600 hover:underline truncate block"
                          >
                            {ref.url}
                          </a>
                        </div>
                        <a 
                          href={ref.url} 
                          target="_blank" 
                          rel="noopener noreferrer" 
                          className="p-2.5 bg-gray-50 text-gray-600 group-hover:bg-blue-600 group-hover:text-white rounded-xl transition-all shrink-0"
                          title="Open Resource"
                        >
                          <ExternalLink size={18} />
                        </a>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        ) : (
          
          /* SUMMARY & RESEARCH CHAT VIEW */
          <div className="space-y-6">
            {currentMessages.map((msg) => (
              <div key={msg.id} className={`flex gap-4 max-w-3xl ${msg.role === 'user' ? 'ml-auto flex-row-reverse' : ''}`}>
                <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 mt-1 ${
                  msg.role === 'user' ? 'bg-gray-800 text-white' : 'bg-blue-600 text-white'
                }`}>
                  {msg.role === 'user' ? <User size={18} /> : <Bot size={18} />}
                </div>
                <div className="flex flex-col gap-1">
                  <span className={`font-semibold text-sm ${msg.role === 'user' ? 'text-right' : 'text-left'} text-gray-800`}>
                    {msg.role === 'user' ? 'You' : 'EduAgent'}
                  </span>
                  <div className={`p-4 rounded-2xl shadow-sm text-gray-700 ${
                    msg.role === 'user' ? 'bg-blue-600 text-white rounded-tr-none' : 'bg-white border border-gray-100 rounded-tl-none'
                  }`}>
                    {msg.content}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {activeChat?.agentProgress && (
          <div className="flex gap-4 max-w-3xl items-center text-blue-600 bg-blue-50/50 p-4 rounded-2xl border border-blue-100">
            <Bot size={18} className="animate-pulse shrink-0" />
            <span className="text-sm font-medium animate-pulse">
              {activeChat.agentProgress}
            </span>
          </div>
        )}

        {/* Your existing isProcessing block */}
        {isProcessing && !activeChat?.agentProgress && (
          <div className="flex gap-4 max-w-3xl items-center text-gray-400 text-sm italic">
            <Bot size={18} className="animate-spin text-blue-600" />
            EduAgent is generating response...
          </div>
        )}
      </div>

      {/* Fixed Input Area */}
      <div className="p-4 bg-white border-t border-gray-100 shrink-0">
        <form onSubmit={handleSendMessage} className="max-w-4xl mx-auto relative flex items-center">
          <input 
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            placeholder={
              activeTool === 'reference' 
                ? "Enter a topic to generate references..." 
                : activeTool === 'summary'
                  ? "Ask a question about the document..."
                  : "What topic do you want to research about..."
            }
            className="w-full pl-5 pr-14 py-4 bg-gray-50 border border-gray-200 rounded-2xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
          />
          <button 
            type="submit"
            disabled={!inputValue.trim() || isProcessing}
            className="absolute right-3 p-2 bg-blue-600 text-white rounded-xl hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {activeTool === 'reference' ? <ArrowRight size={20} /> : <Send size={20} />}
          </button>
        </form>
        <p className="text-center text-xs text-gray-400 mt-3">
          AI agents can make mistakes. Please verify important information.
        </p>
      </div>
    </div>
  );
}