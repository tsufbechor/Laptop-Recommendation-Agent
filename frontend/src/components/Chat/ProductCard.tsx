import { motion, AnimatePresence } from "framer-motion";
import { Check, ChevronDown, Cpu, HardDrive, Info, MemoryStick, Monitor, Sparkles, Target, TrendingUp, X } from "lucide-react";
import { useState } from "react";
import { RetrievedProduct } from "../../types";
import { cn } from "../../utils/cn";

interface ProductCardProps {
  product: RetrievedProduct;
  index?: number;
}

const ProductCard: React.FC<ProductCardProps> = ({ product, index = 0 }) => {
  const [showDetails, setShowDetails] = useState(false);
  const similarityPercent = Math.round(product.similarity * 100);
  const isHighMatch = similarityPercent >= 80;
  const isMediumMatch = similarityPercent >= 60;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20, scale: 0.95 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ delay: index * 0.1, duration: 0.4, ease: "easeOut" }}
      whileHover={{ scale: 1.02, y: -2 }}
      className="group relative overflow-hidden rounded-2xl border border-white/10 bg-gradient-to-br from-slate-900/90 to-slate-800/50 p-5 shadow-glass backdrop-blur-xl transition-all duration-300 hover:border-primary/30 hover:shadow-glow-sm"
    >
      {/* Shimmer effect on hover */}
      <div className="absolute inset-0 -translate-x-full bg-shimmer bg-[length:200%_100%] opacity-0 transition-all duration-700 group-hover:translate-x-full group-hover:opacity-30"></div>

      {/* Top badge - similarity score */}
      <div className="mb-4 flex items-start justify-between">
        <div className="flex items-center gap-2">
          <motion.div
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ delay: index * 0.1 + 0.2, type: "spring", stiffness: 200 }}
            className={cn(
              "flex items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-semibold ring-1",
              isHighMatch
                ? "bg-accent/10 text-accent ring-accent/20"
                : isMediumMatch
                  ? "bg-primary/10 text-primary ring-primary/20"
                  : "bg-slate-700/50 text-slate-300 ring-slate-600/50"
            )}
          >
            {isHighMatch && <Sparkles className="h-3.5 w-3.5" />}
            {similarityPercent}% Match
          </motion.div>
        </div>
        <div className="rounded-full bg-primary/10 px-2.5 py-1 text-xs font-medium text-primary-300">
          {product.vendor}
        </div>
      </div>

      {/* Product name and price */}
      <div className="mb-3">
        <h3 className="mb-1 text-lg font-semibold leading-tight text-white group-hover:text-primary-300 transition-colors">
          {product.name}
        </h3>
        <div className="flex items-baseline gap-2">
          <span className="text-2xl font-bold text-accent">
            {Number.isFinite(product.price) ? `$${product.price.toLocaleString()}` : "Price unavailable"}
          </span>
          {product.matched_keywords && product.matched_keywords.length > 0 && (
            <div className="flex items-center gap-1 text-xs text-slate-400">
              <TrendingUp className="h-3 w-3" />
              {product.matched_keywords.length} match{product.matched_keywords.length > 1 ? "es" : ""}
            </div>
          )}
        </div>
      </div>

      {/* Product Image */}
      {product.image_url && (
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: index * 0.1 + 0.15, duration: 0.4 }}
          className="mb-4 overflow-hidden rounded-xl bg-slate-800/50 ring-1 ring-white/5"
        >
          <img
            src={product.image_url}
            alt={product.name}
            className="h-48 w-full object-cover transition-transform duration-500 group-hover:scale-105"
            onError={(e) => {
              e.currentTarget.style.display = 'none';
            }}
          />
        </motion.div>
      )}

      {/* Explanation */}
      {product.explanation && (
        <p className="mb-4 text-sm leading-relaxed text-slate-300">
          {product.explanation}
        </p>
      )}

      {/* Specs grid */}
      <div className="grid grid-cols-2 gap-3">
        <div className="flex items-start gap-2 rounded-lg bg-slate-800/50 p-2.5 ring-1 ring-white/5">
          <Cpu className="mt-0.5 h-4 w-4 flex-shrink-0 text-primary-400" />
          <div className="min-w-0">
            <div className="text-[10px] font-medium uppercase tracking-wider text-slate-500">CPU</div>
            <div className="truncate text-xs font-medium text-slate-200">{product.cpu}</div>
          </div>
        </div>

        <div className="flex items-start gap-2 rounded-lg bg-slate-800/50 p-2.5 ring-1 ring-white/5">
          <Monitor className="mt-0.5 h-4 w-4 flex-shrink-0 text-accent-purple" />
          <div className="min-w-0">
            <div className="text-[10px] font-medium uppercase tracking-wider text-slate-500">GPU</div>
            <div className="truncate text-xs font-medium text-slate-200">{product.gpu}</div>
          </div>
        </div>

        <div className="flex items-start gap-2 rounded-lg bg-slate-800/50 p-2.5 ring-1 ring-white/5">
          <MemoryStick className="mt-0.5 h-4 w-4 flex-shrink-0 text-accent-cyan" />
          <div className="min-w-0">
            <div className="text-[10px] font-medium uppercase tracking-wider text-slate-500">RAM</div>
            <div className="truncate text-xs font-medium text-slate-200">{product.ram}</div>
          </div>
        </div>

        <div className="flex items-start gap-2 rounded-lg bg-slate-800/50 p-2.5 ring-1 ring-white/5">
          <HardDrive className="mt-0.5 h-4 w-4 flex-shrink-0 text-accent-pink" />
          <div className="min-w-0">
            <div className="text-[10px] font-medium uppercase tracking-wider text-slate-500">Storage</div>
            <div className="truncate text-xs font-medium text-slate-200">{product.storage}</div>
          </div>
        </div>
      </div>

      {/* Knowledge base sections */}
      {product.knowledge && (
        <>
          {/* Key Strengths */}
          {product.knowledge.strengths && product.knowledge.strengths.length > 0 && (
            <div className="mt-4">
              <div className="mb-2 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-slate-400">
                <Sparkles className="h-3.5 w-3.5" />
                Key Strengths
              </div>
              <div className="space-y-1.5">
                {product.knowledge.strengths.slice(0, 3).map((strength, i) => (
                  <motion.div
                    key={i}
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: index * 0.1 + 0.4 + i * 0.05 }}
                    className="flex items-start gap-2 text-sm text-slate-300"
                  >
                    <Check className="mt-0.5 h-4 w-4 flex-shrink-0 text-accent" />
                    <span>{strength}</span>
                  </motion.div>
                ))}
              </div>
            </div>
          )}

          {/* Best For */}
          {product.knowledge.use_cases && product.knowledge.use_cases.length > 0 && (
            <div className="mt-4">
              <div className="mb-2 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-slate-400">
                <Target className="h-3.5 w-3.5" />
                Best For
              </div>
              <div className="flex flex-wrap gap-1.5">
                {product.knowledge.use_cases.slice(0, 3).map((useCase, i) => (
                  <motion.span
                    key={i}
                    initial={{ opacity: 0, scale: 0.8 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ delay: index * 0.1 + 0.5 + i * 0.05 }}
                    className="rounded-full bg-accent/10 px-2.5 py-1 text-xs font-medium text-accent-300 ring-1 ring-accent/20"
                  >
                    {useCase}
                  </motion.span>
                ))}
              </div>
            </div>
          )}

          {/* More Details Button */}
          {product.knowledge && (product.knowledge.summary || product.knowledge.weaknesses?.length > 0) && (
            <div className="mt-4">
              <button
                onClick={() => setShowDetails(!showDetails)}
                className="flex w-full items-center justify-between rounded-lg bg-slate-800/50 px-3 py-2 text-sm font-medium text-slate-300 ring-1 ring-white/5 transition-all hover:bg-slate-700/50 hover:text-white hover:ring-primary/30"
              >
                <span className="flex items-center gap-2">
                  <Info className="h-4 w-4" />
                  {showDetails ? "Hide Details" : "More Details"}
                </span>
                <motion.div
                  animate={{ rotate: showDetails ? 180 : 0 }}
                  transition={{ duration: 0.2 }}
                >
                  <ChevronDown className="h-4 w-4" />
                </motion.div>
              </button>

              {/* Expandable Details Section */}
              <AnimatePresence>
                {showDetails && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: "auto", opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    transition={{ duration: 0.3 }}
                    className="overflow-hidden"
                  >
                    <div className="mt-3 space-y-4 rounded-lg bg-slate-800/30 p-4 ring-1 ring-white/5">
                      {/* Full Summary */}
                      {product.knowledge.summary && (
                        <div>
                          <div className="mb-2 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-slate-400">
                            <Info className="h-3.5 w-3.5" />
                            Full Summary
                          </div>
                          <p className="text-sm leading-relaxed text-slate-300">{product.knowledge.summary}</p>
                        </div>
                      )}

                      {/* All Strengths */}
                      {product.knowledge.strengths && product.knowledge.strengths.length > 3 && (
                        <div>
                          <div className="mb-2 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-slate-400">
                            <Sparkles className="h-3.5 w-3.5" />
                            All Strengths ({product.knowledge.strengths.length})
                          </div>
                          <div className="space-y-1.5">
                            {product.knowledge.strengths.slice(3).map((strength, i) => (
                              <div key={i} className="flex items-start gap-2 text-sm text-slate-300">
                                <Check className="mt-0.5 h-4 w-4 flex-shrink-0 text-accent" />
                                <span>{strength}</span>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Weaknesses */}
                      {product.knowledge.weaknesses && product.knowledge.weaknesses.length > 0 && (
                        <div>
                          <div className="mb-2 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-slate-400">
                            <X className="h-3.5 w-3.5" />
                            Considerations
                          </div>
                          <div className="space-y-1.5">
                            {product.knowledge.weaknesses.map((weakness, i) => (
                              <div key={i} className="flex items-start gap-2 text-sm text-slate-300">
                                <X className="mt-0.5 h-4 w-4 flex-shrink-0 text-orange-400" />
                                <span>{weakness}</span>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* All Use Cases */}
                      {product.knowledge.use_cases && product.knowledge.use_cases.length > 3 && (
                        <div>
                          <div className="mb-2 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-slate-400">
                            <Target className="h-3.5 w-3.5" />
                            All Use Cases ({product.knowledge.use_cases.length})
                          </div>
                          <div className="flex flex-wrap gap-1.5">
                            {product.knowledge.use_cases.slice(3).map((useCase, i) => (
                              <span
                                key={i}
                                className="rounded-full bg-slate-700/50 px-2.5 py-1 text-xs font-medium text-slate-300 ring-1 ring-white/10"
                              >
                                {useCase}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          )}
        </>
      )}

      {/* Matched keywords */}
      {product.matched_keywords && product.matched_keywords.length > 0 && (
        <div className="mt-4 flex flex-wrap gap-1.5">
          {product.matched_keywords.slice(0, 4).map((keyword, i) => (
            <motion.span
              key={keyword}
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: index * 0.1 + 0.3 + i * 0.05 }}
              className="rounded-full bg-primary/10 px-2 py-0.5 text-[10px] font-medium text-primary-300 ring-1 ring-primary/20"
            >
              {keyword}
            </motion.span>
          ))}
        </div>
      )}

      {/* Glow effect for high matches */}
      {isHighMatch && (
        <div className="pointer-events-none absolute -inset-px rounded-2xl bg-gradient-to-r from-accent/20 to-primary/20 opacity-0 transition-opacity duration-500 group-hover:opacity-100"></div>
      )}
    </motion.div>
  );
};

export default ProductCard;
