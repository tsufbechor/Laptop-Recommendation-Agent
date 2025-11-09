import { motion } from "framer-motion";
import { ArrowRight, DollarSign, TrendingDown, TrendingUp } from "lucide-react";
import { RetrievedProduct } from "../../types";

interface ProductComparisonProps {
  primary: RetrievedProduct;
  alternative: RetrievedProduct;
  index?: number;
}

const ProductComparison: React.FC<ProductComparisonProps> = ({ primary, alternative, index = 0 }) => {
  const primaryHasPrice = Number.isFinite(primary.price);
  const alternativeHasPrice = Number.isFinite(alternative.price);
  const primaryPriceValue = primaryHasPrice ? primary.price : null;
  const alternativePriceValue = alternativeHasPrice ? alternative.price : null;
  const priceDiff =
    primaryPriceValue !== null && alternativePriceValue !== null ? alternativePriceValue - primaryPriceValue : null;
  const priceDiffPercent =
    priceDiff !== null && primaryPriceValue !== null && primaryPriceValue !== 0
      ? Math.round((Math.abs(priceDiff) / primaryPriceValue) * 100)
      : null;
  const primaryPriceDisplay = primaryHasPrice ? `$${primary.price.toLocaleString()}` : "Price unavailable";
  const alternativePriceDisplay = alternativeHasPrice ? `$${alternative.price.toLocaleString()}` : "Price unavailable";

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.1 + 0.2 }}
      className="overflow-hidden rounded-2xl border border-white/10 bg-gradient-to-br from-primary-900/20 to-accent-900/10 shadow-glass backdrop-blur-xl"
    >
      <div className="border-b border-white/10 bg-glass-dark/30 px-5 py-3">
        <div className="flex items-center justify-center gap-2">
          <span className="text-sm font-semibold text-slate-300">Product Comparison</span>
          <ArrowRight className="h-4 w-4 text-primary-400" />
        </div>
      </div>

      <div className="grid grid-cols-3 gap-4 p-5">
        {/* Primary Product */}
        <div className="text-center">
          <div className="mb-2 inline-block rounded-full bg-primary/10 px-3 py-1 text-xs font-semibold text-primary-300 ring-1 ring-primary/20">
            Primary Pick
          </div>
          <h4 className="mb-2 text-sm font-semibold text-white">{primary.name}</h4>
          {primary.image_url && (
            <div className="mb-3 overflow-hidden rounded-lg bg-slate-800/50 ring-1 ring-white/5">
              <img
                src={primary.image_url}
                alt={primary.name}
                className="h-32 w-full object-cover"
                onError={(e) => {
                  e.currentTarget.style.display = 'none';
                }}
              />
            </div>
          )}
          <div className="text-xl font-bold text-accent">{primaryPriceDisplay}</div>
        </div>

        {/* Comparison Middle */}
        <div className="flex flex-col items-center justify-center space-y-2">
          {/* Price Difference */}
          <div className="flex items-center gap-2 rounded-lg bg-slate-800/50 px-3 py-2 text-center ring-1 ring-white/5">
            <DollarSign className="h-4 w-4 text-slate-400" />
            <div>
              <div className="text-xs text-slate-400">Price Difference</div>
              {priceDiff !== null ? (
                <div className={`text-sm font-bold ${priceDiff > 0 ? "text-accent" : "text-orange-400"}`}>
                  {priceDiff > 0 ? "+" : "-"}${Math.abs(priceDiff).toLocaleString()}
                  {priceDiffPercent !== null && ` (${priceDiffPercent}%)`}
                </div>
              ) : (
                <div className="text-sm font-medium text-slate-500">Price data unavailable</div>
              )}
            </div>
          </div>

          {/* Quick Comparison */}
          {primary.knowledge && alternative.knowledge && (
            <div className="w-full space-y-1.5 text-xs">
              {/* Performance Comparison */}
              <div className="flex items-center justify-between rounded bg-slate-800/30 px-2 py-1">
                <span className="text-slate-400">Performance</span>
                {primary.cpu.includes("Ultra") || primary.cpu.includes("i9") ? (
                  <TrendingUp className="h-3.5 w-3.5 text-accent" />
                ) : (
                  <TrendingDown className="h-3.5 w-3.5 text-slate-400" />
                )}
              </div>

              {/* Value */}
              <div className="flex items-center justify-between rounded bg-slate-800/30 px-2 py-1">
                <span className="text-slate-400">Value</span>
                {priceDiff !== null ? (
                  priceDiff > 0 ? (
                    <TrendingUp className="h-3.5 w-3.5 text-accent" />
                  ) : (
                    <TrendingDown className="h-3.5 w-3.5 text-slate-400" />
                  )
                ) : (
                  <TrendingDown className="h-3.5 w-3.5 text-slate-500" />
                )}
              </div>
            </div>
          )}
        </div>

        {/* Alternative Product */}
        <div className="text-center">
          <div className="mb-2 inline-block rounded-full bg-accent/10 px-3 py-1 text-xs font-semibold text-accent-300 ring-1 ring-accent/20">
            Alternative
          </div>
          <h4 className="mb-2 text-sm font-semibold text-white">{alternative.name}</h4>
          {alternative.image_url && (
            <div className="mb-3 overflow-hidden rounded-lg bg-slate-800/50 ring-1 ring-white/5">
              <img
                src={alternative.image_url}
                alt={alternative.name}
                className="h-32 w-full object-cover"
                onError={(e) => {
                  e.currentTarget.style.display = 'none';
                }}
              />
            </div>
          )}
          <div className="text-xl font-bold text-accent">{alternativePriceDisplay}</div>
        </div>
      </div>

      {/* Key Differences */}
      {primary.knowledge && alternative.knowledge && (
        <div className="border-t border-white/10 bg-slate-900/30 px-5 py-4">
          <div className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-400">Key Differences</div>
          <div className="grid grid-cols-2 gap-4 text-xs">
            {/* Primary Advantages */}
            <div>
              <div className="mb-1.5 font-medium text-primary-300">{primary.vendor} {primary.family}</div>
              <ul className="space-y-1 text-slate-400">
                {primary.knowledge.strengths?.slice(0, 2).map((strength, i) => (
                  <li key={i} className="flex items-start gap-1.5">
                    <span className="mt-1 h-1 w-1 flex-shrink-0 rounded-full bg-primary-400"></span>
                    <span>{strength}</span>
                  </li>
                ))}
              </ul>
            </div>

            {/* Alternative Advantages */}
            <div>
              <div className="mb-1.5 font-medium text-accent-300">{alternative.vendor} {alternative.family}</div>
              <ul className="space-y-1 text-slate-400">
                {alternative.knowledge.strengths?.slice(0, 2).map((strength, i) => (
                  <li key={i} className="flex items-start gap-1.5">
                    <span className="mt-1 h-1 w-1 flex-shrink-0 rounded-full bg-accent-400"></span>
                    <span>{strength}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}
    </motion.div>
  );
};

export default ProductComparison;
