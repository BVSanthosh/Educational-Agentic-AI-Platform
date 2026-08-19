import { create } from 'zustand';
import type { AppState, ToolType, Session, Message, UploadStatus } from '../types';

interface AppStore extends AppState { 
  token: string | null;
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
}
 
export const useAppStore = create<AppStore>((set, get) => ({
  token: localStorage.getItem('token'),

  activeTool: 'reference',
  referenceSpaceId: null,
  activeSessionId: null,
  
  activeChat: null,
  activeReferences: null,

  sessions: {
    summary: [],
    research: [],
  },

  isLeftPanelOpen: true,
  isRightPanelOpen: false,
  isNewSpaceModalOpen: false,

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
      sessions: { summary: [], research: [] } 
    });
  },
  // --------------------
  
  setActiveTool: (tool) => set({ activeTool: tool, activeChat: null, activeReferences: null }), 
  setActiveSessionId: (id) => set({ activeSessionId: id, activeChat: null, activeReferences: null }),

  setLeftPanelOpen: (isOpen) => set({ isLeftPanelOpen: isOpen }),
  setRightPanelOpen: (isOpen) => set({ isRightPanelOpen: isOpen }),
  setNewSpaceModalOpen: (isOpen) => set({ isNewSpaceModalOpen: isOpen }),

  loadSpaceData: async (spaceId, tool) => {
    const state = get();
    if (!state.token) return;

    try {
      const response = await fetch(`http://localhost:8000/api/space/${spaceId}`, {
        method: 'GET',
        headers: { 'Authorization': `Bearer ${state.token}` }
      });

      if (!response.ok) throw new Error("Failed to fetch space data");
      
      const spaceResponse = await response.json();
      const data = spaceResponse.data || {};

      if (tool === 'reference') {
        set({ 
          activeReferences: {
            description: data.description || "",
            references: data.references || []
          } 
        });
      } else {
        set({ 
          activeChat: {
            messages: data.messages || []
          } 
        });
      }
    } catch (error) {
      console.error(`Failed to load data for space ${spaceId}:`, error);
    }
  },

  setAgentProgress: (progress) => set((state) => ({
    activeChat: state.activeChat ? { ...state.activeChat, agentProgress: progress } : null
  })),

  setActiveDocument: (documentId) => set((state) => ({
    activeChat: state.activeChat ? { ...state.activeChat, activeDocumentId: documentId } : null,
    isRightPanelOpen: !!documentId // Auto-open the right panel when a doc is ready!
  })),

  createNewSpace: async (tool, spaceName, uploadStatus) => {
    try {
      const state = get();
      const response = await fetch('http://localhost:8000/api/space/', {
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
        activeReferences: null ,
        isNewSpaceModalOpen: false
      });
      
    } catch (error) {
      console.error("Space creation error:", error);
    }
  },

  ensureReferenceSpaceExists: async () => {
    const state = get();
    if (state.referenceSpaceId) return state.referenceSpaceId;

    try {
      const fetchRes = await fetch('http://localhost:8000/api/space/?tool=reference', {
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

      const createRes = await fetch('http://localhost:8000/api/space/', {
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

    } catch (error) {
      console.error("Reference space initialization failed:", error);
      return null;
    }
  },

  fetchSpaces: async () => {
    const state = get();
    if (!state.token) return; 

    try {
      const response = await fetch('http://localhost:8000/api/space/', {
        method: 'GET',
        headers: { 'Authorization': `Bearer ${state.token}` }
      });

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

      set({
        sessions: {
          summary: summarySessions,
          research: researchSessions,
        }
      });

    } catch (error) {
      console.error("Failed to load spaces from backend:", error);
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

    // Optional: Add a simple browser confirmation so users don't accidentally click it
    if (!window.confirm("Are you sure you want to delete this space? This action cannot be undone.")) {
      return;
    }

    try {
      const response = await fetch(`http://localhost:8000/api/space/${spaceId}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${state.token}` }
      });

      if (!response.ok) throw new Error("Failed to delete space");

      // Update the state to remove the space
      set((state) => {
        const updatedSessions = state.sessions[tool].filter(s => s.id !== spaceId);
        
        // If the user deleted the space they are currently looking at, 
        // clear the active session so they don't look at a ghost space!
        const isDeletingActiveSession = state.activeSessionId === spaceId;

        return {
          sessions: {
            ...state.sessions,
            [tool]: updatedSessions
          },
          ...(isDeletingActiveSession ? { 
            activeSessionId: null, 
            activeChat: null 
          } : {})
        };
      });

    } catch (error) {
      console.error(`Failed to delete space ${spaceId}:`, error);
    }
  },
}));