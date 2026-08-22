import { useState, useEffect, useRef } from 'react';
import { useAppStore } from '../store/useAppStore';
import { 
  UploadCloud, 
  Send, 
  Bot, 
  FileText, 
  ArrowRight, 
  User,
  ExternalLink,
  Compass,
  BookOpen
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import type { Message } from '../types'; 

export default function CentreWorkspace() {
  const { 
    activeTool, 
    activeSessionId, 
    sessions, 
    addMessage, 
    updateStreamingMessage, 
    token, 
    ensureReferenceSpaceExists,
    loadSpaceData, 
    activeChat, 
    activeReferences,
    setAgentProgress,
    setActiveDocument,
    addDocumentToActiveChat
  } = useAppStore();

  const fileInputRef = useRef<HTMLInputElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const prevSessionIdRef = useRef(activeSessionId);
  const prevMessagesLength = useRef(0);

  const [inputValue, setInputValue] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);

  const currentViewKey = `${activeTool}-${activeSessionId}`;
  const [prevViewKey, setPrevViewKey] = useState(currentViewKey);

  if (currentViewKey !== prevViewKey) {
    setPrevViewKey(currentViewKey);
    setIsProcessing(false);
    setInputValue('');
  }

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

  // --- AUTO-SCROLL HOOK ---
  const scrollToBottom = (instant = false) => {
    messagesEndRef.current?.scrollIntoView({ 
      behavior: instant ? 'auto' : 'smooth' 
    });
  };

  useEffect(() => {
    const currentLength = activeChat?.messages?.length || 0;
    
    // We want to INSTANT scroll if:
    // A) We just clicked a different space in the sidebar
    // B) The chat history just finished fetching from the database (jumped from 0 to X messages)
    const isSpaceSwitch = prevSessionIdRef.current !== activeSessionId;
    const isHistoryLoad = prevMessagesLength.current === 0 && currentLength > 0 && !isProcessing;
    
    scrollToBottom(isSpaceSwitch || isHistoryLoad);
    
    // Update our trackers for the next render
    prevSessionIdRef.current = activeSessionId;
    prevMessagesLength.current = currentLength;
  }, [activeChat?.messages, activeChat?.agentProgress, isProcessing, activeSessionId]);

  // Handles clicking to select a file
  const onFileSelected = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      if (file.type !== 'application/pdf') {
        alert("Only PDF documents are supported.");
      } else {
        handleFileUpload(file);
      }
    }
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const onDrop = (e: React.DragEvent<HTMLButtonElement>) => {
    e.preventDefault();
    const file = e.dataTransfer.files?.[0];
    if (file) {
      if (file.type !== 'application/pdf') {
        alert("Only PDF documents are supported.");
      } else {
        handleFileUpload(file);
      }
    }
  };

  const onDragOver = (e: React.DragEvent<HTMLButtonElement>) => {
    e.preventDefault();
  };

  const handleFileUpload = async (file: File) => {
    if (!activeSession) return;

    const spaceId = activeSession.id;
    const store = useAppStore.getState();

    // Instantly switch to Chat view and set progress
    store.updateSessionState('summary', spaceId, 'chat');
    store.setAgentProgress("Uploading and parsing document...");

    const formData = new FormData();
    formData.append("file", file);
    formData.append("space_id", spaceId);

    const agentMessageId = crypto.randomUUID();
    let agentMessageAdded = false;
    let accumulatedText = "";

    try {
      const response = await fetch(`http://localhost:8000/api/summary/uploadfile`, {
        method: 'POST',
        headers: { 
          ...(token ? { 'Authorization': `Bearer ${token}` } : {})
        },
        credentials: 'include',
        body: formData 
      });

      if (!response.ok || !response.body) {
        throw new Error('Failed to stream summary response from backend');
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const events = buffer.split('\n\n');
        buffer = events.pop() || ''; 

        for (const event of events) {
          if (event.startsWith('data: ')) {
            try {
              const payload = JSON.parse(event.slice(6));
              const currentStore = useAppStore.getState();

              // Block UI updates if user navigated away during upload
              if (currentStore.activeSessionId !== spaceId) {
                continue;
              }

              if (payload.type === 'progress') {
                currentStore.setAgentProgress(payload.message);
              } 
              else if (payload.type === 'token') {
                if (!agentMessageAdded) {
                  currentStore.addMessage({
                    id: agentMessageId,
                    role: 'agent',
                    content: '',
                  });
                  agentMessageAdded = true;
                  currentStore.setAgentProgress(null); 
                }
                accumulatedText += payload.content;
                currentStore.updateStreamingMessage(agentMessageId, accumulatedText);
              } 
              else if (payload.type === 'document_ready') {
                const docId = payload.document_id || payload.id;
                if (docId) {
                  currentStore.addDocumentToActiveChat({
                    id: docId,
                    filename: payload.filename || file.name
                  });
                  currentStore.setActiveDocument(docId);
                }
              } 
              else if (payload.type === 'error') {
                currentStore.setAgentProgress(`Error: ${payload.message}`);
              } 
              else if (payload.type === 'done') {
                currentStore.setAgentProgress(null);
              }
            } catch (err) {
              console.warn("Failed to parse SSE JSON:", event, err);
            }
          }
        }
      }
    } catch (error) {
      console.error("Upload stream error:", error);
      store.setAgentProgress(null);
      store.updateSessionState('summary', spaceId, 'upload');
    }
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

        // Reset previous references and show progress only
        useAppStore.setState({ activeReferences: null });
        setAgentProgress("Searching and generating academic references...");

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
        
        await loadSpaceData(spaceId, 'reference');
        setAgentProgress(null);
        setIsProcessing(false);
      }
      
      // -------------------------------------------------------------
      // CASE B: Summary & Research Tools (Streaming Chat)
      // -------------------------------------------------------------
      else if (activeSession) {
        const spaceId = activeSession.id;

        const userMessage: Message = {
          id: crypto.randomUUID(),
          role: 'user',
          content: query,
        };
        addMessage(userMessage); 

        const agentMessageId = crypto.randomUUID();
        const store = useAppStore.getState();
        store.setAgentProgress("Analyzing request...");
        setIsProcessing(false);

        const endpoint = activeTool === 'summary' 
          ? `http://localhost:8000/api/summary/${spaceId}/query`
          : `http://localhost:8000/api/research/${spaceId}/stream`;

        const response = await fetch(endpoint, {
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
                // Get the absolutely latest state from the store
                const currentStore = useAppStore.getState();
                
                // If the user switched to a different space, IGNORE the UI updates!
                if (currentStore.activeSessionId !== spaceId) {
                  continue; 
                }

                const payload = JSON.parse(event.slice(6));

                if (payload.type === 'progress') {
                  store.setAgentProgress(payload.message);
                } 
                else if (payload.type === 'token') {
                  if (!agentMessageAdded) {
                    addMessage({
                      id: agentMessageId,
                      role: 'agent',
                      content: '',
                    });
                    agentMessageAdded = true;
                    store.setAgentProgress(null); 
                  }
                  accumulatedText += payload.content;
                  updateStreamingMessage(agentMessageId, accumulatedText);
                } 
                else if (payload.type === 'document_ready') {
                  const docId = payload.document_id || payload.id;
                  if (!docId) return;
                  
                  store.setAgentProgress(null); 
                  addDocumentToActiveChat({
                    id: docId,
                    filename: payload.filename || "Research_Report.md"
                  });
                  setActiveDocument(docId);
                }
                else if (payload.type === 'error') {
                  store.setAgentProgress(`Error: ${payload.message}`);
                }
                else if (payload.type === 'done') {
                  store.setAgentProgress(null);
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

  // --- VIEW 1: Empty State (No Space Selected) ---
  if (activeTool !== 'reference' && !activeSessionId) {
    const isSummary = activeTool === 'summary';
    
    return (
      <div className="flex-1 flex flex-col items-center justify-center text-center p-6 bg-gray-50/50 dark:bg-gray-900/50 transition-colors duration-200">
        <div className="w-16 h-16 bg-blue-50 dark:bg-blue-900/40 text-blue-600 dark:text-blue-400 rounded-3xl flex items-center justify-center mb-6 shadow-inner transition-colors">
          {isSummary ? <FileText size={32} /> : <Compass size={32} />}
        </div>
        <h3 className="text-2xl font-bold text-gray-800 dark:text-gray-100 mb-2 transition-colors">
          {isSummary ? 'Document Summarizer' : 'Deep Research Agent'}
        </h3>
        <p className="text-gray-500 dark:text-gray-400 max-w-md mb-8 leading-relaxed transition-colors">
          {isSummary
            ? 'Create a summary space in the sidebar to upload PDFs, generate comprehensive markdown overviews, and instantly chat with your files.'
            : 'Create a research space in the sidebar to conduct in-depth analysis, gather web sources, and synthesize comprehensive reports.'}
        </p>
        
        <div className="text-sm text-gray-400 dark:text-gray-500 border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-800/50 px-4 py-2 rounded-xl shadow-sm transition-colors">
          Select or create a new <span className="font-semibold text-gray-600 dark:text-gray-300 capitalize">{activeTool} Space</span> to begin
        </div>
      </div>
    );
  }

  // --- VIEW 2: File Upload State ---
  if (activeSession?.state === 'upload') {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-6 transition-colors duration-200">
        <div className="max-w-md w-full">
          <div className="text-center mb-6">
            <h3 className="text-2xl font-bold text-gray-800 dark:text-gray-100 transition-colors">Upload your Document</h3>
            <p className="text-gray-500 dark:text-gray-400 mt-2 transition-colors">Initialize your {activeSession.title} space with a source file.</p>
          </div>
          
          <input 
            type="file" 
            ref={fileInputRef}
            style={{ display: 'none' }} 
            onChange={onFileSelected} 
            accept=".pdf" 
          />

          <button 
            onClick={() => fileInputRef.current?.click()}
            onDragOver={onDragOver}
            onDrop={onDrop}
            className="w-full border-2 border-dashed border-gray-300 dark:border-gray-700 rounded-2xl p-12 flex flex-col items-center justify-center bg-gray-50 dark:bg-gray-900/50 hover:bg-gray-100 dark:hover:bg-gray-800 hover:border-blue-400 dark:hover:border-blue-500 transition-all group"
          >
            <div className="w-16 h-16 bg-white dark:bg-gray-800 shadow-sm rounded-full flex items-center justify-center mb-4 group-hover:scale-105 transition-transform">
              <UploadCloud size={32} className="text-blue-500 dark:text-blue-400" />
            </div>
            <p className="font-medium text-gray-700 dark:text-gray-300 transition-colors">
              Click or drag file to upload
            </p>
            <p className="text-sm text-gray-400 dark:text-gray-500 mt-2 transition-colors">Supports PDF only</p>
          </button>
        </div>
      </div>
    );
  }

  const currentMessages = activeChat?.messages || [];
  const hasReferences = Boolean(
    activeReferences && 
    (activeReferences.description || (activeReferences.references && activeReferences.references.length > 0))
  );

  // --- VIEW 3: Workspace Header & Chat/Reference Interface ---
  return (
    <div className="flex-1 flex flex-col min-h-0 relative bg-white dark:bg-gray-900 transition-colors duration-200">
      {/* SCROLLABLE MAIN CONTENT AREA */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        
        {/* ======================================================== */}
        {/* REFERENCE TOOL VIEW */}
        {/* ======================================================== */}
        {activeTool === 'reference' ? (
          <div className="max-w-3xl mx-auto space-y-6 w-full">
            
            {/* Show intro banner ONLY when there are no references AND we aren't currently processing one */}
            {!hasReferences && !isProcessing && (
              <div className="bg-blue-50/70 dark:bg-blue-900/20 border border-blue-100 dark:border-blue-800/50 p-8 rounded-2xl flex flex-col items-center text-center space-y-3 mt-8 transition-colors">
                <div className="w-12 h-12 rounded-2xl bg-blue-600 dark:bg-blue-500 flex items-center justify-center text-white shadow-sm transition-colors">
                  <BookOpen size={24} />
                </div>
                <h3 className="font-bold text-blue-900 dark:text-blue-100 text-xl transition-colors">Academic Reference Generator</h3>
                <p className="text-blue-700/80 dark:text-blue-300/80 text-sm max-w-md transition-colors">
                  Enter any research topic, question, or keyword in the input bar below to generate formatted references and sources.
                </p>
              </div>
            )}

            {/* Generated References View (Replaces the intro card) */}
            {hasReferences && activeReferences && (
              <div className="space-y-6">
                {activeReferences.references && activeReferences.references.length > 0 && (
                  <div className="space-y-4">
                    {activeReferences.description && (
                      <>
                        <h4 className="font-semibold text-gray-800 dark:text-gray-200 text-lg transition-colors">Overview</h4>
                        <p className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed transition-colors">{activeReferences.description}</p>
                      </>
                    )}
                    <h4 className="font-semibold text-gray-800 dark:text-gray-200 text-lg transition-colors">
                      Resources
                    </h4>
                    {activeReferences.references.map((ref, index) => (
                      <div key={index} className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 p-5 rounded-xl shadow-sm flex items-center justify-between gap-4 group hover:border-blue-300 dark:hover:border-blue-500 transition-colors">
                        <div className="space-y-1 min-w-0">
                          <span className="text-xs font-bold text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/40 px-2.5 py-0.5 rounded-full transition-colors">
                            Ref [{index + 1}]
                          </span>
                          <h5 className="font-semibold text-gray-900 dark:text-gray-100 text-base truncate transition-colors">{ref.title}</h5>
                          <a 
                            href={ref.url} 
                            target="_blank" 
                            rel="noopener noreferrer" 
                            className="text-xs text-blue-600 dark:text-blue-400 hover:underline truncate block transition-colors"
                          >
                            {ref.url}
                          </a>
                        </div>
                        <a 
                          href={ref.url} 
                          target="_blank" 
                          rel="noopener noreferrer" 
                          className="p-2.5 bg-gray-50 dark:bg-gray-700 text-gray-600 dark:text-gray-300 group-hover:bg-blue-600 group-hover:text-white dark:group-hover:bg-blue-600 rounded-xl transition-all shrink-0"
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
          
          /* ======================================================== */
          /* SUMMARY & RESEARCH CHAT VIEW */
          /* ======================================================== */
          <div className="space-y-6 max-w-3xl mx-auto w-full">
            {/* Chat Messages */}
            {currentMessages.map((msg) => (
              <div key={msg.id} className={`flex gap-4 max-w-3xl ${msg.role === 'user' ? 'ml-auto flex-row-reverse' : ''}`}>
                <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 mt-1 ${
                  msg.role === 'user' ? 'bg-gray-800 dark:bg-gray-700 text-white' : 'bg-blue-600 dark:bg-blue-500 text-white'
                } transition-colors`}>
                  {msg.role === 'user' ? <User size={18} /> : <Bot size={18} />}
                </div>
                <div className="flex flex-col gap-1 max-w-[85%]">
                  <span className={`font-semibold text-sm ${msg.role === 'user' ? 'text-right' : 'text-left'} text-gray-800 dark:text-gray-300 transition-colors`}>
                    {msg.role === 'user' ? 'You' : 'EduAgent'}
                  </span>
                  
                  <div className={`p-4 rounded-2xl shadow-sm transition-colors ${
                    msg.role === 'user' 
                      ? 'bg-blue-600 text-white rounded-tr-none' 
                      : 'bg-white dark:bg-gray-800 border border-gray-100 dark:border-gray-700 text-gray-800 dark:text-gray-200 rounded-tl-none'
                  }`}>
                    {msg.role === 'user' ? (
                      <div className="whitespace-pre-wrap">{msg.content}</div>
                    ) : (
                      <div className="prose prose-sm md:prose-base prose-blue dark:prose-invert max-w-none">
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>
                          {msg.content}
                        </ReactMarkdown>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Dynamic Agent Progress Banner */}
        {activeChat?.agentProgress && (
          <div className="flex gap-4 max-w-3xl items-center text-blue-600 dark:text-blue-400 bg-blue-50/50 dark:bg-blue-900/20 p-4 rounded-2xl border border-blue-100 dark:border-blue-800/50 mx-auto w-full transition-colors">
            <Bot size={18} className="animate-pulse shrink-0" />
            <span className="text-sm font-medium animate-pulse">
              {activeChat.agentProgress}
            </span>
          </div>
        )}

        {/* Processing Spinner Fallback */}
        {isProcessing && !activeChat?.agentProgress && (
          <div className="flex gap-4 max-w-3xl items-center text-gray-400 dark:text-gray-500 text-sm italic mx-auto w-full transition-colors">
            <Bot size={18} className="animate-spin text-blue-600 dark:text-blue-400" />
            EduAgent is generating response...
          </div>
        )}

        {/* Invisible scroll anchor */}
        <div ref={messagesEndRef} />
      </div>

      {/* Fixed Input Area */}
      <div className="p-4 bg-white dark:bg-gray-900 border-t border-gray-100 dark:border-gray-800 shrink-0 transition-colors duration-200">
        <form onSubmit={handleSendMessage} className="max-w-3xl mx-auto w-full relative flex items-center">
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
            className="w-full pl-5 pr-14 py-4 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-2xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all text-gray-800 dark:text-gray-100 placeholder-gray-400 dark:placeholder-gray-500"
          />
          <button 
            type="submit"
            disabled={!inputValue.trim() || isProcessing}
            className="absolute right-3 p-2 bg-blue-600 dark:bg-blue-500 text-white rounded-xl hover:bg-blue-700 dark:hover:bg-blue-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {activeTool === 'reference' ? <ArrowRight size={20} /> : <Send size={20} />}
          </button>
        </form>
        <p className="text-center text-xs text-gray-400 dark:text-gray-500 mt-3 transition-colors">
          AI agents can make mistakes. Please verify important information.
        </p>
      </div>
    </div>
  );
}