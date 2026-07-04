import { create } from "zustand";

export interface ConversationResponse {
  id: string;
  tenant_id: string;
  customer_id: string;
  platform: string;
  channel_type: string;
  message_in: string | null;
  message_out: string | null;
  intent: string | null;
  sentiment: string | null;
  is_human_takeover: boolean;
  escalation_reason: string | null;
  created_at: string;
}

type Filter = "all" | "ai" | "human";

interface InboxStore {
  conversations: ConversationResponse[];
  filter: Filter;
  setConversations: (c: ConversationResponse[]) => void;
  setFilter: (f: Filter) => void;
  toggleTakeover: (id: string, value: boolean) => void;
}

export const useInboxStore = create<InboxStore>((set) => ({
  conversations: [],
  filter: "all",
  setConversations: (conversations) => set({ conversations }),
  setFilter: (filter) => set({ filter }),
  toggleTakeover: (id, value) =>
    set((state) => ({
      conversations: state.conversations.map((c) =>
        c.id === id ? { ...c, is_human_takeover: value } : c
      ),
    })),
}));
