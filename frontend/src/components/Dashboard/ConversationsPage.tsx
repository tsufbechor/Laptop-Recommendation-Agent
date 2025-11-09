import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { MessageSquare, Star, ArrowRight, Calendar } from "lucide-react";

interface ConversationFeedback {
  rating: number;
  comment?: string;
  timestamp: string;
}

interface ConversationSummary {
  session_id: string;
  started_at: string;
  updated_at: string;
  message_count: number;
  products_recommended: string[];
  feedback?: ConversationFeedback;
  first_user_message?: string;
}

interface ConversationsPageProps {
  onSelectConversation: (id: string) => void;
}

export const ConversationsPage: React.FC<ConversationsPageProps> = ({
  onSelectConversation,
}) => {
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchConversations();
  }, []);

  const fetchConversations = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await fetch("/api/chat/conversations");
      if (!response.ok) {
        throw new Error("Failed to fetch conversations");
      }
      const data = await response.json();
      setConversations(data);
    } catch (err) {
      console.error("Failed to fetch conversations:", err);
      setError("Failed to load conversations. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

    if (diffDays === 0) {
      return `Today at ${date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}`;
    } else if (diffDays === 1) {
      return `Yesterday at ${date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}`;
    } else if (diffDays < 7) {
      return `${diffDays} days ago`;
    } else {
      return date.toLocaleDateString([], { month: "short", day: "numeric", year: "numeric" });
    }
  };

  return (
    <div className="mx-auto max-w-4xl space-y-6 p-6">
      <div className="mb-8">
        <h1 className="mb-2 text-3xl font-bold text-white">Past Conversations</h1>
        <p className="text-slate-400">Review your previous product recommendation sessions</p>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-20">
          <div className="text-center">
            <div className="mb-4 inline-block h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent"></div>
            <p className="text-slate-400">Loading conversations...</p>
          </div>
        </div>
      ) : error ? (
        <div className="rounded-2xl border border-red-500/20 bg-red-500/10 p-6 text-center">
          <p className="text-red-400">{error}</p>
          <button
            onClick={fetchConversations}
            className="mt-4 text-sm text-red-300 underline hover:text-red-200"
          >
            Try again
          </button>
        </div>
      ) : conversations.length === 0 ? (
        <div className="rounded-2xl border border-white/10 bg-gradient-to-br from-slate-900/90 to-slate-800/50 p-12 text-center">
          <MessageSquare className="mx-auto mb-4 h-12 w-12 text-slate-600" />
          <p className="text-lg text-slate-400">No conversations yet</p>
          <p className="mt-2 text-sm text-slate-500">
            Start chatting to see your history here!
          </p>
        </div>
      ) : (
        <div className="grid gap-4">
          {conversations.map((conv, index) => (
            <motion.div
              key={conv.session_id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.05 }}
              className="group cursor-pointer rounded-2xl border border-white/10 bg-gradient-to-br from-slate-900/90 to-slate-800/50 p-5 shadow-glass backdrop-blur-xl transition-all hover:border-primary/30 hover:shadow-glow-sm"
              onClick={() => onSelectConversation(conv.session_id)}
            >
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="mb-2 flex items-center gap-3">
                    <MessageSquare className="h-5 w-5 text-primary" />
                    <div className="flex items-center gap-2 text-xs text-slate-500">
                      <Calendar className="h-3.5 w-3.5" />
                      <span>{formatDate(conv.started_at)}</span>
                    </div>
                  </div>

                  {conv.first_user_message && (
                    <p className="mb-3 line-clamp-2 text-sm text-slate-300">
                      {conv.first_user_message}
                    </p>
                  )}

                  <div className="flex items-center gap-4 text-xs text-slate-400">
                    <span>{conv.message_count} messages</span>
                    <span>•</span>
                    <span>{conv.products_recommended.length} products recommended</span>
                  </div>

                  {conv.feedback && (
                    <div className="mt-3 flex items-center gap-2">
                      <div className="flex gap-1">
                        {Array.from({ length: 5 }).map((_, i) => (
                          <Star
                            key={i}
                            className={`h-3 w-3 ${
                              i < conv.feedback!.rating
                                ? "fill-accent text-accent"
                                : "text-slate-600"
                            }`}
                          />
                        ))}
                      </div>
                      {conv.feedback.comment && (
                        <span className="text-xs text-slate-500">• With comment</span>
                      )}
                    </div>
                  )}
                </div>

                <ArrowRight className="h-5 w-5 text-slate-600 transition-colors group-hover:text-primary" />
              </div>
            </motion.div>
          ))}
        </div>
      )}
    </div>
  );
};
