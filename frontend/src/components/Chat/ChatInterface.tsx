import { useCallback, useEffect, useRef, useState } from "react";
import { Loader2, RefreshCw, WifiOff, Zap, Clock, Database } from "lucide-react";
import { motion } from "framer-motion";

import { connectStreamingChat } from "../../services/api";
import { ChatMetadata, ComparisonResponse, RetrievedProduct } from "../../types";
import { useChat } from "../../context/ChatContext";
import { Button } from "../ui/button";
import Card, { CardContent, CardHeader, CardTitle } from "../ui/card";
import { Badge } from "../ui/badge";
import MessageList from "./MessageList";
import InputBox from "./InputBox";
import { FeedbackModal } from "./FeedbackModal";

const ChatInterface = () => {
  const { sessionId, messages, addMessage, updateMessage, isStreaming, setStreaming, resetConversation } = useChat();
  const [reasoning, setReasoning] = useState<string | null>(null);
  const [metadata, setMetadata] = useState<ChatMetadata | null>(null);
  const [products, setProducts] = useState<RetrievedProduct[]>([]);
  const [comparison, setComparison] = useState<ComparisonResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showFeedbackModal, setShowFeedbackModal] = useState(false);
  const [feedbackGiven, setFeedbackGiven] = useState(false);
  const cleanupRef = useRef<(() => void) | null>(null);

  useEffect(() => () => cleanupRef.current?.(), []);

  const randomId = useCallback(() => {
    if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
      return crypto.randomUUID();
    }
    return `${Date.now()}`;
  }, []);

  const handleSendMessage = useCallback(
    (text: string) => {
      if (isStreaming) {
        return;
      }

      setError(null);
      const userMessageId = `${sessionId}-user-${randomId()}`;
      addMessage({ id: userMessageId, role: "user", content: text });

      const assistantMessageId = `${sessionId}-assistant-${randomId()}`;
      addMessage({ id: assistantMessageId, role: "assistant", content: "", streaming: true });

      setStreaming(true);
      cleanupRef.current = connectStreamingChat(
        sessionId,
        text,
        {
          onMetadata: (data) =>
            setMetadata((prev) => ({
              ...prev,
              top_k: prev?.top_k ?? 0,
              retrieval_latency_ms: data.retrieval_latency_ms,
              applied_filters: data.filters ?? {}
            })),
          onChunk: (chunk) => {
            updateMessage(assistantMessageId, (message) => ({
              ...message,
              content: `${message.content}${chunk}`
            }));
          },
          onComplete: (payload) => {
            setProducts(payload.products);
            setReasoning(payload.reasoning ?? null);
            setComparison(payload.comparison ?? null);
            setMetadata((prev) => ({
              ...(prev ?? { top_k: payload.products.length, applied_filters: {} }),
              top_k: payload.products.length,
              llm_latency_ms: payload.llm_latency_ms
            }));
            updateMessage(assistantMessageId, (message) => ({
              ...message,
              content: payload.reply,
              streaming: false
            }));
            setStreaming(false);
            cleanupRef.current = null;
          },
          onError: (message) => {
            const errorMessage = message ?? "Connection interrupted. Please try again.";
            setError(errorMessage);
            setStreaming(false);
            updateMessage(assistantMessageId, (message) => ({
              ...message,
              content: errorMessage || "I ran into a connection issue. Could you retry?",
              streaming: false
            }));
            cleanupRef.current = null;
          }
        },
        {}
      );
    },
    [addMessage, isStreaming, randomId, sessionId, setStreaming, updateMessage]
  );

  const handleReset = () => {
    cleanupRef.current?.();
    setProducts([]);
    setMetadata(null);
    setReasoning(null);
    setComparison(null);
    setError(null);
    setFeedbackGiven(false);
    setShowFeedbackModal(false);
    resetConversation();
  };

  const handleFeedbackSubmit = async (rating: number, comment: string) => {
    try {
      const response = await fetch("/api/chat/feedback/submit", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: sessionId,
          rating,
          comment: comment || undefined,
        }),
      });

      if (!response.ok) {
        throw new Error("Failed to submit feedback");
      }

      setFeedbackGiven(true);
    } catch (error) {
      console.error("Failed to submit feedback:", error);
      throw error;
    }
  };

  // Show feedback modal after products are shown
  useEffect(() => {
    if (products.length > 0 && !feedbackGiven && !isStreaming) {
      // Show feedback modal after a short delay
      const timer = setTimeout(() => {
        setShowFeedbackModal(true);
      }, 2000);
      return () => clearTimeout(timer);
    }
  }, [products, feedbackGiven, isStreaming]);

  return (
    <div className="grid gap-6 lg:grid-cols-[2fr,1fr]">
      {/* Main chat container */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="flex h-[75vh] flex-col overflow-hidden rounded-3xl border border-white/10 bg-gradient-to-br from-slate-900/90 to-slate-800/50 shadow-glass backdrop-blur-2xl"
      >
        {/* Header */}
        <div className="flex items-center justify-end border-b border-white/10 bg-glass-dark/30 px-6 py-4 backdrop-blur-xl">
          <div className="flex items-center gap-3">
            {isStreaming ? (
              <motion.div
                initial={{ scale: 0.9, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                className="flex items-center gap-2 rounded-full bg-accent/10 px-3 py-1.5 ring-1 ring-accent/20"
              >
                <Loader2 className="h-3.5 w-3.5 animate-spin text-accent" />
                <span className="text-xs font-semibold text-accent">Streaming</span>
              </motion.div>
            ) : (
              <div className="flex items-center gap-2 rounded-full bg-slate-700/30 px-3 py-1.5 ring-1 ring-white/10">
                <div className="h-2 w-2 rounded-full bg-slate-400"></div>
                <span className="text-xs font-semibold text-slate-400">Ready</span>
              </div>
            )}
            <Button
              variant="ghost"
              size="sm"
              onClick={handleReset}
              disabled={isStreaming}
              className="gap-2 rounded-full hover:bg-glass-light hover:shadow-glow-sm transition-all"
            >
              <RefreshCw className="h-4 w-4" />
              <span className="hidden sm:inline">New Chat</span>
            </Button>
          </div>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-hidden px-6 py-6">
          <MessageList messages={messages} isStreaming={isStreaming} products={products} reasoning={reasoning} comparison={comparison} />
        </div>

        {/* Input */}
        <div className="border-t border-white/10 bg-glass-dark/30 px-6 py-4 backdrop-blur-xl">
          <InputBox onSend={handleSendMessage} disabled={isStreaming} />
          {error && (
            <motion.p
              initial={{ opacity: 0, y: -5 }}
              animate={{ opacity: 1, y: 0 }}
              className="mt-2 text-xs font-medium text-rose-400"
            >
              {error}
            </motion.p>
          )}
        </div>
      </motion.div>

      {/* Sidebar */}
      <motion.aside
        initial={{ opacity: 0, x: 20 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.5, delay: 0.1 }}
        className="space-y-4"
      >
        {/* Insights Card */}
        <div className="overflow-hidden rounded-2xl border border-white/10 bg-gradient-to-br from-slate-900/90 to-slate-800/50 shadow-glass backdrop-blur-2xl">
          <div className="border-b border-white/10 bg-glass-dark/30 px-5 py-4 backdrop-blur-xl">
            <div className="flex items-center gap-2">
              <Zap className="h-4 w-4 text-primary" />
              <h3 className="font-semibold text-white">Performance</h3>
            </div>
          </div>
          <div className="space-y-4 p-5">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-sm text-slate-400">
                <Database className="h-4 w-4" />
                <span>Messages</span>
              </div>
              <span className="text-lg font-bold text-white">{messages.length}</span>
            </div>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-sm text-slate-400">
                <Clock className="h-4 w-4" />
                <span>RAG</span>
              </div>
              <span className="font-mono text-sm font-semibold text-accent">
                {metadata?.retrieval_latency_ms ? `${metadata.retrieval_latency_ms.toFixed(0)}ms` : "—"}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-sm text-slate-400">
                <Zap className="h-4 w-4" />
                <span>LLM</span>
              </div>
              <span className="font-mono text-sm font-semibold text-primary">
                {metadata?.llm_latency_ms ? `${metadata.llm_latency_ms.toFixed(0)}ms` : "—"}
              </span>
            </div>
          </div>
        </div>

        {/* Quick Stats */}
        {products.length > 0 && (
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.3 }}
            className="overflow-hidden rounded-2xl border border-white/10 bg-gradient-to-br from-primary/10 to-accent-purple/5 p-5 shadow-glass backdrop-blur-2xl"
          >
            <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-primary-300">
              {products.length} System{products.length > 1 ? "s" : ""} Matched
            </p>
            <div className="space-y-2">
              {products.slice(0, 2).map((product, i) => (
                <motion.div
                  key={product.sku}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: i * 0.1 }}
                  className="flex items-center justify-between text-sm"
                >
                  <span className="truncate text-slate-200">{product.name}</span>
                  <span className="ml-2 flex-shrink-0 font-semibold text-accent">
                    {Number.isFinite(product.price) ? `$${product.price.toLocaleString()}` : "Price unavailable"}
                  </span>
                </motion.div>
              ))}
            </div>
          </motion.div>
        )}
      </motion.aside>

      {/* Feedback Modal */}
      <FeedbackModal
        isOpen={showFeedbackModal}
        onClose={() => setShowFeedbackModal(false)}
        sessionId={sessionId}
        onSubmit={handleFeedbackSubmit}
      />
    </div>
  );
};

export default ChatInterface;
