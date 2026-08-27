import { create } from 'zustand';
import type { AppState, ToolType, Session, Message, UploadStatus, DocumentMeta } from '../types';
import toast from 'react-hot-toast';
import { API_BASE_URL } from '../api/config';

interface AppStore extends AppState { 
  toggleTheme: () => void;
  setToken: (token: string | null) => void; 
  logout: () => void;

  setActiveTool: (tool: ToolType) => void;
  setActiveSessionId: (id: string | null) => void;
  setLeftPanelOpen: (isOpen: boolean) => void;
  setRightPanelOpen: (isOpen: boolean) => void;
  setNewSpaceModalOpen: (isOpen: boolean) => void;

  ensureReferenceSpaceExists: () => Promise<string | null>;
  fetchSpaces: () => Promise<void>;
  loadSpaceData: (spaceId: string, tool: ToolType) => Promise<void>;
  
  createNewSpace: (tool: 'summary' | 'research', spaceName: string, uploadStatus: UploadStatus) => Promise<void>;
  updateSessionState: (tool: 'summary' | 'research', sessionId: string, state: UploadStatus) => void;
  addMessage: (message: Message) => void; 
  updateStreamingMessage: (messageId: string, content: string) => void;
  deleteSpace: (spaceId: string, tool: 'summary' | 'research') => Promise<void>;

  setAgentProgress: (progress: string | null) => void;
  setActiveDocument: (documentId: string | null) => void;
  addDocumentToActiveChat: (document: DocumentMeta) => void;

  initLiveStream: (spaceId: string, messageId: string) => void;
  updateLiveStreamProgress: (spaceId: string, progress: string | null) => void;
  updateLiveStreamText: (spaceId: string, text: string) => void;
  endLiveStream: (spaceId: string) => void;
}
 
export const useAppStore = create<AppStore>((set, get) => ({
  token: localStorage.getItem('token'),
  theme: (localStorage.getItem('theme') as 'light' | 'dark') || 'light',

  activeDocumentId: null,

  activeTool: 'reference',
  referenceSpaceId: null,
  activeSessionId: null,
  
  activeChat: null,
  activeReferences: null,

  liveStreams: {},

  sessions: {
    summary: [],
    research: [],
  },

  isLeftPanelOpen: true,
  isRightPanelOpen: false,
  isNewSpaceModalOpen: false,

  toggleTheme: () => set((state) => {
    const newTheme = state.theme === 'light' ? 'dark' : 'light';
    localStorage.setItem('theme', newTheme);
    return { theme: newTheme };
  }),

  // --- Auth Actions ---
  setToken: (token) => {
    if (token) {
      localStorage.setItem('token', token);
    } else {
      localStorage.removeItem('token');
    }
    set({ token });
  },
  
  logout: () => {
    localStorage.removeItem('token');
    set({ 
      token: null, 
      activeSessionId: null,
      activeTool: 'reference', 
      activeChat: null,      
      activeReferences: null,
      activeDocumentId: null, 
      isRightPanelOpen: false,
      sessions: { summary: [], research: [] } 
    });
  },
  // --------------------
  
  setActiveTool: (tool) => set((state) => {
    // If the tool hasn't changed, do nothing! (Stops screen wipe)
    if (state.activeTool === tool) return state;
     
    return { 
      activeTool: tool, 
      activeChat: null, 
      activeReferences: null,
      activeDocumentId: null, 
      isRightPanelOpen: false
    };
  }), 

  setActiveSessionId: (id) => set((state) => {
    // If the space hasn't changed, do nothing! (Stops screen wipe)
    if (state.activeSessionId === id) return state;
    
    return { 
      activeSessionId: id, 
      activeChat: null, 
      activeReferences: null,
      activeDocumentId: null, 
      isRightPanelOpen: false
    };
  }),

  setLeftPanelOpen: (isOpen) => set({ isLeftPanelOpen: isOpen }),
  setRightPanelOpen: (isOpen) => set({ isRightPanelOpen: isOpen }),
  setNewSpaceModalOpen: (isOpen) => set({ isNewSpaceModalOpen: isOpen }),

  loadSpaceData: async (spaceId, tool) => {
    const state = get();
    if (!state.token) return;

    try {
      const response = await fetch(`${API_BASE_URL}/api/space/${spaceId}`, {
        method: 'GET',
        headers: { 'Authorization': `Bearer ${state.token}` }
      });

      if (!response.ok) throw new Error("Failed to fetch space data");
      
      const spaceResponse = await response.json();

      if (tool === 'reference') {
        set({ 
          activeReferences: {
            description: spaceResponse.data?.description || "",
            references: spaceResponse.data?.references || []
          } 
        });
      } else {
        const documents = spaceResponse.documents || [];
        
        set({ 
          activeChat: {
            messages: spaceResponse.data?.messages || [],
            documents: documents 
          },
          activeDocumentId: null 
        });
      }
    } catch {
      toast.error("Failed to load data");
    }
  },

  setAgentProgress: (progress) => set((state) => ({
    activeChat: state.activeChat ? { ...state.activeChat, agentProgress: progress } : null
  })),

  // Perfectly structured for your button clicks!
  setActiveDocument: (documentId) => set((state) => ({
    activeDocumentId: documentId,
    // Safely open the panel if an ID is passed. If null (Back button), keep it open.
    isRightPanelOpen: documentId ? true : state.isRightPanelOpen 
  })),

  addDocumentToActiveChat: (document) => set((state) => {
    if (!state.activeChat) return state;

    // Prevent duplicates just in case the backend emits twice
    const exists = state.activeChat.documents?.some(d => d.id === document.id);
    if (exists) return state;

    return {
      activeChat: {
        ...state.activeChat,
        documents: [...(state.activeChat.documents || []), document]
      }
    };
  }),

  createNewSpace: async (tool, spaceName, uploadStatus) => {
    try {
      const state = get();
      const response = await fetch(`${API_BASE_URL}/api/space/`, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          ...(state.token ? { 'Authorization': `Bearer ${state.token}` } : {})
        },
        body: JSON.stringify({ tool: tool, name: spaceName, upload_status: uploadStatus }) 
      });

      if (!response.ok) throw new Error(`HTTP error!`);
      const newSpace = await response.json();
      await state.fetchSpaces();

      set({ 
        activeTool: tool, 
        activeSessionId: newSpace.id,
        activeChat: null, 
        activeReferences: null,
        activeDocumentId: null, 
        isRightPanelOpen: false,
        isNewSpaceModalOpen: false
      });
      
    } catch {
      toast.error("Failed to create new space");
    }
  },

  ensureReferenceSpaceExists: async () => {
    const state = get();
    if (state.referenceSpaceId) return state.referenceSpaceId;

    try {
      const fetchRes = await fetch(`${API_BASE_URL}/api/space/?tool=reference`, {
        headers: { 'Authorization': `Bearer ${state.token}` }
      });

      if (fetchRes.ok) {
        const spaces = await fetchRes.json();
        const existingRef = spaces.find((s: { id: string; name: string, tool: string, created_at: string }) => s.tool === 'reference');
        if (existingRef) {
          set({ referenceSpaceId: existingRef.id });
          return existingRef.id;
        }
      }

      const createRes = await fetch(`${API_BASE_URL}/api/space/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${state.token}`
        },
        body: JSON.stringify({ tool: 'reference', name: 'Global Reference', upload_status: 'chat' })
      });

      if (!createRes.ok) throw new Error("Failed to create reference space");
      const newSpace = await createRes.json();

      set({ referenceSpaceId: newSpace.id });
      return newSpace.id;

    } catch {
      toast.error("Failed to initialise Reference space");
      return null;
    }
  },

  fetchSpaces: async () => {
    const state = get();
    if (!state.token) return; 

    try {
      const response = await fetch(`${API_BASE_URL}/api/space/`, {
        method: 'GET',
        headers: { 'Authorization': `Bearer ${state.token}` }
      });

      // 👇 THE FIX: If the token is dead, clear it and abort!
      if (response.status === 401 || response.status === 403) {
        console.warn("Token expired or invalid. Logging out...");
        state.logout(); 
        return;
      }

      if (!response.ok) throw new Error("Failed to fetch spaces");
      
      const spaces = await response.json();

      const summarySessions: Session[] = [];
      const researchSessions: Session[] = [];

      spaces.forEach((space: { id: string; name: string; tool: string; upload_status: UploadStatus; created_at: string }) => {
        if (space.tool === 'reference') return;

        const session: Session = {
          id: space.id,
          title: space.name, 
          createdAt: new Date(space.created_at).getTime(),
          state: space.upload_status, 
        };

        if (space.tool === 'summary') {
          summarySessions.push(session);
        } else if (space.tool === 'research') {
          researchSessions.push(session);
        }
      });

      // Sort both arrays so newest comes first
      const sortByNewest = (a: Session, b: Session) => b.createdAt - a.createdAt;

      set({
        sessions: {
          summary: summarySessions.sort(sortByNewest),
          research: researchSessions.sort(sortByNewest),
        }
      });

    } catch {
      toast.error("Failed to load spaces");
    }
  },

  updateSessionState: (tool, id, newState) => set((state) => ({
    sessions: {
      ...state.sessions,
      [tool]: state.sessions[tool].map(session => 
        session.id === id ? { ...session, state: newState } : session
      )
    }
  })),

  addMessage: (message) => set((state) => ({
    activeChat: state.activeChat 
      ? { ...state.activeChat, messages: [...state.activeChat.messages, message] }
      : { messages: [message] }
  })),

  updateStreamingMessage: (messageId, content) => set((state) => ({
    activeChat: state.activeChat 
      ? {
          ...state.activeChat,
          messages: state.activeChat.messages.map(msg => 
            msg.id === messageId ? { ...msg, content } : msg
          )
        }
      : null
  })),

  deleteSpace: async (spaceId, tool) => {
    const state = get();
    if (!state.token) return;

    try {
      const response = await fetch(`${API_BASE_URL}/api/space/${spaceId}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${state.token}` }
      });

      if (!response.ok) throw new Error("Failed to delete space");

      set((state) => {
        const updatedSessions = state.sessions[tool].filter(s => s.id !== spaceId);
        const isDeletingActiveSession = state.activeSessionId === spaceId;

        return {
          sessions: {
            ...state.sessions,
            [tool]: updatedSessions
          },
          ...(isDeletingActiveSession ? { 
            activeSessionId: null, 
            activeChat: null,
            activeDocumentId: null, // Close panel if active space is deleted
            isRightPanelOpen: false
          } : {})
        };
      });

    } catch {
      toast.error("Failed to delete space");
    }
  },

  initLiveStream: (spaceId, messageId) => set((state) => ({
    liveStreams: {
      ...state.liveStreams,
      [spaceId]: { isProcessing: true, progress: null, accumulatedText: '', messageId }
    }
  })),

  updateLiveStreamProgress: (spaceId, progress) => set((state) => {
    const stream = state.liveStreams[spaceId];
    if (!stream) return state;
    
    // Check if the user is currently looking at this space
    const isCurrentSpace = state.activeSessionId === spaceId;
    
    return {
      liveStreams: {
        ...state.liveStreams,
        [spaceId]: { ...stream, progress }
      },
      // Instantly update the UI if they are looking at it
      activeChat: (isCurrentSpace && state.activeChat) 
        ? { ...state.activeChat, agentProgress: progress } 
        : state.activeChat
    };
  }),

  updateLiveStreamText: (spaceId, text) => set((state) => {
    const stream = state.liveStreams[spaceId];
    if (!stream) return state;

    // Check if the user is currently looking at this space
    const isCurrentSpace = state.activeSessionId === spaceId;
    
    return {
      liveStreams: {
        ...state.liveStreams,
        [spaceId]: { ...stream, accumulatedText: text }
      },
      // Instantly update the chat bubble if they are looking at it
      activeChat: (isCurrentSpace && state.activeChat)
        ? {
            ...state.activeChat,
            messages: state.activeChat.messages.map(msg => 
              msg.id === stream.messageId ? { ...msg, content: text } : msg
            )
          }
        : state.activeChat
    };
  }),

  endLiveStream: (spaceId) => set((state) => {
    // 1. Create a shallow copy of the current streams
    const remainingStreams = { ...state.liveStreams };
    
    // 2. Delete the specific stream from the copy
    delete remainingStreams[spaceId];
    
    const isCurrentSpace = state.activeSessionId === spaceId;
    
    return {
      liveStreams: remainingStreams,
      // Clear the progress banner from the UI if they are looking at it
      activeChat: (isCurrentSpace && state.activeChat)
        ? { ...state.activeChat, agentProgress: null }
        : state.activeChat
    };
  }),
}));