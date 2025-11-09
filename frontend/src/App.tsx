import { useState } from "react";
import { MessageSquare, BarChart3, History } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

import ChatInterface from "./components/Chat/ChatInterface";
import MetricsDashboard from "./components/Dashboard/MetricsDashboard";
import { ConversationsPage } from "./components/Dashboard/ConversationsPage";
import { buttonVariants } from "./components/ui/button";
import { cn } from "./utils/cn";

type ViewMode = "chat" | "metrics" | "conversations";

const App = () => {
  const [view, setView] = useState<ViewMode>("chat");

  return (
    <div className="relative min-h-screen overflow-hidden bg-background">
      {/* Ambient gradient background */}
      <div className="fixed inset-0 -z-10">
        <div className="absolute inset-0 bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950"></div>
        <div className="absolute left-1/4 top-0 h-96 w-96 animate-pulse-slow rounded-full bg-primary/5 blur-3xl"></div>
        <div className="absolute bottom-0 right-1/4 h-96 w-96 animate-pulse-slow rounded-full bg-accent-purple/5 blur-3xl" style={{ animationDelay: "1s" }}></div>
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-primary/5 via-transparent to-transparent"></div>
      </div>

      {/* Header */}
      <motion.header
        initial={{ y: -20, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ duration: 0.5 }}
        className="sticky top-0 z-50 border-b border-white/10 bg-glass-dark/50 backdrop-blur-2xl"
      >
        <div className="mx-auto flex w-full max-w-7xl items-center justify-between px-6 py-4">
          <motion.div
            initial={{ x: -20, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            transition={{ delay: 0.1 }}
            className="flex items-center gap-4"
          >
            <motion.div
              whileHover={{ scale: 1.05, y: -2 }}
              whileTap={{ scale: 0.95 }}
              className="relative group"
            >
              {/* Glow effect behind logo */}
              <div className="absolute -inset-4 rounded-3xl bg-gradient-to-r from-primary/25 via-accent-purple/20 to-primary/25 opacity-0 blur-2xl transition-opacity duration-500 group-hover:opacity-100"></div>

              {/* Logo container */}
              <div className="relative flex h-20 w-96 items-center justify-center rounded-2xl bg-gradient-to-br from-slate-800/80 to-slate-900/80 px-6 py-3 shadow-glow-sm ring-1 ring-white/10 backdrop-blur-sm transition-all group-hover:ring-primary/30">
                <img
                  src="/automatiq-logo.png"
                  alt="Automatiq.ai Logo"
                  className="h-full w-full object-contain transition-transform duration-300 group-hover:scale-110"
                />
              </div>
            </motion.div>
            <div>
              <h1 className="bg-gradient-to-r from-white via-slate-200 to-slate-300 bg-clip-text text-xl font-bold tracking-tight text-transparent">
                Automatiq.ai
              </h1>
              <p className="text-sm text-slate-400">Laptop Shopping Assistant</p>
            </div>
          </motion.div>
          <motion.div
            initial={{ x: 20, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            transition={{ delay: 0.2 }}
            className="flex gap-2"
          >
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              className={cn(
                buttonVariants({ variant: view === "chat" ? "primary" : "ghost" }),
                "gap-2 rounded-xl transition-all",
                view === "chat" && "shadow-glow-sm"
              )}
              onClick={() => setView("chat")}
            >
              <MessageSquare className="h-4 w-4" />
              Chat
            </motion.button>
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              className={cn(
                buttonVariants({ variant: view === "metrics" ? "primary" : "ghost" }),
                "gap-2 rounded-xl transition-all",
                view === "metrics" && "shadow-glow-sm"
              )}
              onClick={() => setView("metrics")}
            >
              <BarChart3 className="h-4 w-4" />
              Metrics
            </motion.button>
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              className={cn(
                buttonVariants({ variant: view === "conversations" ? "primary" : "ghost" }),
                "gap-2 rounded-xl transition-all",
                view === "conversations" && "shadow-glow-sm"
              )}
              onClick={() => setView("conversations")}
            >
              <History className="h-4 w-4" />
              History
            </motion.button>
          </motion.div>
        </div>
      </motion.header>

      {/* Main content with view transitions */}
      <main className="mx-auto w-full max-w-7xl px-6 py-8">
        <AnimatePresence mode="wait">
          {view === "chat" && (
            <motion.div
              key="chat"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ duration: 0.3 }}
            >
              <ChatInterface />
            </motion.div>
          )}
          {view === "metrics" && (
            <motion.div
              key="metrics"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ duration: 0.3 }}
            >
              <MetricsDashboard onBack={() => setView("chat")} />
            </motion.div>
          )}
          {view === "conversations" && (
            <motion.div
              key="conversations"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ duration: 0.3 }}
            >
              <ConversationsPage
                onSelectConversation={(id) => {
                  // Switch to chat view when a conversation is selected
                  setView("chat");
                }}
              />
            </motion.div>
          )}
        </AnimatePresence>
      </main>
    </div>
  );
};

export default App;
