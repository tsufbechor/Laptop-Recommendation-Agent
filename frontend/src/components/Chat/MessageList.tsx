import { useEffect, useRef } from "react";
import { motion } from "framer-motion";
import { Sparkles } from "lucide-react";

import { ChatMessage, ComparisonResponse, RetrievedProduct } from "../../types";
import { ScrollArea } from "../ui/scroll-area";
import MessageBubble from "./MessageBubble";
import ProductCard from "./ProductCard";
import ProductComparison from "./ProductComparison";

interface MessageListProps {
  messages: ChatMessage[];
  isStreaming: boolean;
  products: RetrievedProduct[];
  reasoning: string | null;
  comparison?: ComparisonResponse | null;
}

const MessageList: React.FC<MessageListProps> = ({
  messages,
  isStreaming,
  products,
  reasoning,
  comparison,
}) => {
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isStreaming]);

  return (
    <ScrollArea className="h-full pr-2">
      <div className="flex h-full flex-col gap-5">
        {messages.length === 0 && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
            className="mt-20 rounded-2xl border border-dashed border-primary/20 bg-gradient-to-br from-slate-900/50 to-slate-800/30 p-10 text-center backdrop-blur-sm"
          >
            <motion.div
              animate={{ rotate: [0, 10, -10, 0] }}
              transition={{ duration: 4, repeat: Infinity, repeatType: "reverse" }}
              className="mb-4 inline-flex rounded-full bg-primary/10 p-4"
            >
              <Sparkles className="h-8 w-8 text-primary" />
            </motion.div>
            <p className="text-lg font-medium text-slate-200">
              Ready to find your perfect system?
            </p>
            <p className="mt-2 text-sm text-slate-400">
              Tell me about your needs and I'll recommend the best match for you.
            </p>
          </motion.div>
        )}
        {messages.map((message) => (
          <MessageBubble key={message.id} message={message} isStreaming={isStreaming && !!message.streaming} />
        ))}
        {reasoning && (
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.3 }}
            className="rounded-2xl border border-primary/20 bg-gradient-to-br from-primary/10 to-accent-purple/5 p-5 shadow-glass backdrop-blur-xl"
          >
            <div className="mb-2 flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-primary" />
              <p className="text-xs font-semibold uppercase tracking-wider text-primary-300">Why these systems</p>
            </div>
            <p className="text-sm leading-relaxed text-slate-200">{reasoning}</p>
          </motion.div>
        )}
        {products.length > 0 && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.4 }}
            className="space-y-4"
          >
            <div className="flex items-center gap-2">
              <div className="h-px flex-1 bg-gradient-to-r from-transparent via-primary/30 to-transparent"></div>
              <p className="text-xs font-semibold uppercase tracking-wider text-primary-300">
                {comparison ? "Side-by-Side Comparison" : "Recommended Systems"}
              </p>
              <div className="h-px flex-1 bg-gradient-to-r from-transparent via-primary/30 to-transparent"></div>
            </div>

            {/* Show comparison if we have exactly 2 products */}
            {products.length === 2 ? (
              <>
                <ProductComparison primary={products[0]} alternative={products[1]} index={0} />
                <div className="mt-4 grid gap-4 md:grid-cols-2">
                  {products.map((product, index) => (
                    <ProductCard key={product.sku} product={product} index={index} />
                  ))}
                </div>
              </>
            ) : (
              products.slice(0, 3).map((product, index) => (
                <ProductCard key={product.sku} product={product} index={index} />
              ))
            )}
          </motion.div>
        )}
        <div ref={endRef} />
      </div>
    </ScrollArea>
  );
};

export default MessageList;
