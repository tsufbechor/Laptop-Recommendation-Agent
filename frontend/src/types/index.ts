export type MessageRole = "user" | "assistant" | "system";

export interface ChatMessage {
  id: string;
  role: MessageRole;
  content: string;
  timestamp?: string;
  streaming?: boolean;
}

export interface Product {
  sku: string;
  vendor: string;
  family: string;
  name: string;
  description: string;
  cpu: string;
  gpu: string;
  storage: string;
  ram: string;
  price: number;
  image_url?: string;
}

export interface ProductKnowledge {
  sku: string;
  summary: string;
  strengths: string[];
  weaknesses: string[];
  use_cases: string[];
  last_updated: string;
}

export interface RetrievedProduct extends Product {
  similarity: number;
  matched_keywords?: string[];
  explanation?: string | null;
  knowledge?: ProductKnowledge | null;
}

export interface ChatMetadata {
  retrieval_latency_ms?: number;
  llm_latency_ms?: number;
  top_k: number;
  applied_filters: Record<string, unknown>;
}

export interface ProductComparison {
  better_at: string[];
  worse_at: string[];
  price_difference: number;
  value_assessment: string;
}

export interface ComparedProduct extends RetrievedProduct {
  comparison?: ProductComparison;
  is_primary_recommendation: boolean;
}

export interface ComparisonResponse {
  primary_product: ComparedProduct;
  alternative_product: ComparedProduct;
  comparison_summary: string;
  recommendation_reasoning: string;
}

export interface ChatReplyPayload {
  reply: string;
  reasoning?: string | null;
  products_shown: RetrievedProduct[];
  metadata: ChatMetadata;
  comparison?: ComparisonResponse | null;
}

export interface SessionMetrics {
  session_id: string;
  turn_count: number;
  retrieval_latency_ms: number;
  llm_latency_ms: number;
  recommended_products: string[];
  user_feedback: Record<string, "positive" | "negative">;
  started_at: string;
  updated_at: string;
}

export interface AggregateMetrics {
  total_sessions: number;
  average_turns: number;
  average_retrieval_latency_ms: number;
  average_llm_latency_ms: number;
  most_recommended_products: string[];
  positive_feedback_ratio?: number | null;
}

export interface FeedbackPayload {
  session_id: string;
  message_id: string;
  feedback: "positive" | "negative";
}
