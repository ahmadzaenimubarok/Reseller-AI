import { useEffect } from "react";
import api from "@/lib/api";
import { useInboxStore, type ConversationResponse } from "@/store/inbox";

export function useConversations() {
  const { filter, setConversations, toggleTakeover } = useInboxStore();

  useEffect(() => {
    const params: Record<string, string> = {};
    if (filter === "ai") params.is_human_takeover = "false";
    if (filter === "human") params.is_human_takeover = "true";

    function fetchConversations() {
      api
        .get<{ data: ConversationResponse[] }>("/conversations", { params })
        .then((res) => setConversations(res.data.data))
        .catch(() => {});
    }

    fetchConversations();
    const timer = setInterval(fetchConversations, 10_000);
    return () => clearInterval(timer);
  }, [filter, setConversations]);

  async function handleToggle(id: string, currentValue: boolean) {
    const newValue = !currentValue;
    toggleTakeover(id, newValue);
    try {
      await api.patch(`/conversations/${id}/takeover`, {
        is_human_takeover: newValue,
      });
    } catch {
      toggleTakeover(id, currentValue);
    }
  }

  return { handleToggle };
}
