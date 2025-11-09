import { Bot, User } from "lucide-react";
import { motion } from "framer-motion";

import { ChatMessage } from "../../types";
import { cn } from "../../utils/cn";

interface MessageBubbleProps {
  message: ChatMessage;
  isStreaming?: boolean;
}

const TypingIndicator = () => (
  <div className="flex items-center gap-1 py-1">
    <span className="h-2 w-2 animate-typing rounded-full bg-primary/60" style={{ animationDelay: "0ms" }}></span>
    <span className="h-2 w-2 animate-typing rounded-full bg-primary/60" style={{ animationDelay: "200ms" }}></span>
    <span className="h-2 w-2 animate-typing rounded-full bg-primary/60" style={{ animationDelay: "400ms" }}></span>
  </div>
);

const MessageBubble: React.FC<MessageBubbleProps> = ({ message, isStreaming }) => {
  const isUser = message.role === "user";

  return (
    <motion.div
      initial={{ opacity: 0, y: 10, scale: 0.95 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ duration: 0.3, ease: "easeOut" }}
      className={cn("flex w-full gap-3", isUser ? "justify-end" : "justify-start")}
    >
      {!isUser && (
        <motion.div
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          transition={{ delay: 0.1, type: "spring", stiffness: 200 }}
          className="mt-1 flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-primary/20 to-accent-purple/20 text-primary shadow-glow-sm ring-1 ring-white/10"
        >
          <Bot className="h-5 w-5" />
        </motion.div>
      )}
      <motion.div
        whileHover={{ scale: 1.01 }}
        className={cn(
          "group relative max-w-[75%] rounded-2xl px-5 py-3.5 text-[15px] shadow-glass backdrop-blur-xl transition-all duration-200",
          isUser
            ? "ml-auto rounded-tr-sm bg-gradient-to-br from-primary to-primary-600 text-white shadow-glow-sm"
            : "rounded-tl-sm border border-white/10 bg-glass-light text-slate-100"
        )}
      >
        <div className="whitespace-pre-wrap leading-relaxed">
          {message.content}
          {isStreaming && !message.content && <TypingIndicator />}
        </div>
        {isStreaming && message.content && (
          <div className="mt-2 flex items-center gap-2 text-xs text-slate-400">
            <TypingIndicator />
          </div>
        )}
        {message.timestamp && (
          <div className="mt-2 text-[10px] font-medium uppercase tracking-wider text-slate-500 opacity-0 transition-opacity group-hover:opacity-100">
            {new Date(message.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
          </div>
        )}
      </motion.div>
      {isUser && (
        <motion.div
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          transition={{ delay: 0.1, type: "spring", stiffness: 200 }}
          className="mt-1 flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-slate-700 to-slate-800 text-slate-300 ring-1 ring-white/10"
        >
          <User className="h-5 w-5" />
        </motion.div>
      )}
    </motion.div>
  );
};

export default MessageBubble;
