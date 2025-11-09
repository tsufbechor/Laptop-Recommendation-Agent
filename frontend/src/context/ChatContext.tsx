import React, { createContext, useCallback, useContext, useMemo, useState } from "react";

import { ChatMessage } from "../types";

interface ChatContextValue {
  sessionId: string;
  messages: ChatMessage[];
  isStreaming: boolean;
  setStreaming: (value: boolean) => void;
  addMessage: (message: ChatMessage) => void;
  updateMessage: (messageId: string, updater: (message: ChatMessage) => ChatMessage) => void;
  resetConversation: () => void;
}

const ChatContext = createContext<ChatContextValue | undefined>(undefined);

const generateSessionId = () => {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return `session-${Date.now()}`;
};

interface ChatProviderProps {
  children: React.ReactNode;
}

export const ChatProvider: React.FC<ChatProviderProps> = ({ children }) => {
  const [sessionId, setSessionId] = useState<string>(generateSessionId);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);

  const resetConversation = useCallback(() => {
    setSessionId(generateSessionId());
    setMessages([]);
    setIsStreaming(false);
  }, []);

  const addMessage = useCallback((message: ChatMessage) => {
    setMessages((current) => [...current, message]);
  }, []);

  const updateMessage = useCallback((messageId: string, updater: (message: ChatMessage) => ChatMessage) => {
    setMessages((current) =>
      current.map((message) => {
        if (message.id !== messageId) {
          return message;
        }
        return updater(message);
      })
    );
  }, []);

  const setStreaming = useCallback((value: boolean) => setIsStreaming(value), []);

  const value = useMemo(
    () => ({
      sessionId,
      messages,
      isStreaming,
      setStreaming,
      addMessage,
      updateMessage,
      resetConversation
    }),
    [sessionId, messages, isStreaming, addMessage, updateMessage, resetConversation]
  );

  return <ChatContext.Provider value={value}>{children}</ChatContext.Provider>;
};

export const useChat = (): ChatContextValue => {
  const context = useContext(ChatContext);
  if (!context) {
    throw new Error("useChat must be used within a ChatProvider");
  }
  return context;
};
