import axios from "axios";

import {
  AggregateMetrics,
  ChatReplyPayload,
  ComparisonResponse,
  FeedbackPayload,
  RetrievedProduct,
  SessionMetrics
} from "../types";

const api = axios.create({
  baseURL: "/api",
  headers: {
    "Content-Type": "application/json"
  }
});

interface SendMessageOptions {
  userPreferences?: Record<string, unknown>;
}

export const sendMessage = async (
  sessionId: string,
  message: string,
  options: SendMessageOptions = {}
): Promise<ChatReplyPayload> => {
  const response = await api.post<ChatReplyPayload>("/chat/message", {
    session_id: sessionId,
    message,
    user_preferences: options.userPreferences
  });
  return response.data;
};

export const sendFeedback = async (payload: FeedbackPayload) => {
  await api.post("/chat/feedback", payload);
};

export const getMetrics = async (): Promise<AggregateMetrics> => {
  const response = await api.get<AggregateMetrics>("/metrics/aggregate");
  return response.data;
};

export const listSessions = async (): Promise<string[]> => {
  const response = await api.get<{ sessions: string[] }>("/metrics/sessions");
  return response.data.sessions;
};

export const getSessionMetrics = async (sessionId: string): Promise<SessionMetrics> => {
  const response = await api.get<SessionMetrics>(`/metrics/session/${sessionId}`);
  return response.data;
};

export const getSessionHistory = async (sessionId: string) => {
  const response = await api.get<{ session_id: string; messages: { id: string; role: string; content: string }[] }>(
    `/chat/history/${sessionId}`
  );
  return response.data.messages;
};

interface StreamingCallbacks {
  onChunk: (chunk: string) => void;
  onMetadata?: (metadata: { retrieval_latency_ms?: number; filters?: Record<string, unknown> }) => void;
  onComplete: (payload: { reply: string; reasoning?: string | null; products: RetrievedProduct[]; llm_latency_ms?: number; comparison?: ComparisonResponse | null }) => void;
  onError?: (message?: string) => void;
}

export const connectStreamingChat = (
  sessionId: string,
  message: string,
  callbacks: StreamingCallbacks,
  userPreferences?: Record<string, unknown>
) => {
  const wsProtocol = window.location.protocol === "https:" ? "wss" : "ws";
  const wsUrl = `${wsProtocol}://${window.location.host}/api/chat/stream`;
  const socket = new WebSocket(wsUrl);
  let hasCompleted = false;
  let manuallyClosed = false;

  const cleanup = () => {
    manuallyClosed = true;
    if (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING) {
      socket.close();
    }
  };

  socket.onopen = () => {
    socket.send(
      JSON.stringify({
        session_id: sessionId,
        message,
        user_preferences: userPreferences
      })
    );
  };

  socket.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      if (data.type === "chunk") {
        callbacks.onChunk(data.data);
      } else if (data.type === "metadata") {
        callbacks.onMetadata?.(data.data);
      } else if (data.type === "complete") {
        hasCompleted = true;
        callbacks.onComplete(data.data);
      } else if (data.type === "error") {
        hasCompleted = true;
        callbacks.onError?.(data.data?.message ?? "Streaming session failed. Please try again.");
        cleanup();
      }
    } catch (error) {
      console.error("Failed to parse streaming payload", error);
    }
  };

  socket.onerror = () => {
    if (!hasCompleted) {
      hasCompleted = true;
      callbacks.onError?.("Connection interrupted. Please try again.");
    }
  };

  socket.onclose = () => {
    if (!hasCompleted && !manuallyClosed) {
      callbacks.onError?.("Connection closed before completion.");
    }
  };

  return cleanup;
};
