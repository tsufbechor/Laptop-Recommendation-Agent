import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, Download, TrendingUp } from "lucide-react";

import { getMetrics, getSessionMetrics, listSessions } from "../../services/api";
import { AggregateMetrics, SessionMetrics } from "../../types";
import { Button } from "../ui/button";
import Card, { CardContent, CardHeader, CardTitle } from "../ui/card";

interface MetricsDashboardProps {
  onBack?: () => void;
}

const MetricsDashboard: React.FC<MetricsDashboardProps> = ({ onBack }) => {
  const [selectedSession, setSelectedSession] = useState<string | null>(null);

  const metricsQuery = useQuery<AggregateMetrics>({
    queryKey: ["metrics", "aggregate"],
    queryFn: getMetrics
  });

  const sessionsQuery = useQuery<string[]>({
    queryKey: ["metrics", "sessions"],
    queryFn: listSessions
  });

  const sessionMetricsQuery = useQuery<SessionMetrics | null>({
    queryKey: ["metrics", "session", selectedSession],
    queryFn: async () => {
      if (!selectedSession) return null;
      return getSessionMetrics(selectedSession);
    },
    enabled: !!selectedSession
  });

  const aggregate = metricsQuery.data;
  const sessionMetrics = sessionMetricsQuery.data ?? undefined;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs uppercase tracking-wide text-slate-400">Monitoring</p>
          <h1 className="text-2xl font-semibold text-white">Conversation Metrics</h1>
          <p className="text-sm text-slate-400">
            Track LLM performance, retrieval efficiency, and user sentiment over every session.
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="ghost" className="gap-2" onClick={onBack}>
            <ArrowLeft className="h-4 w-4" />
            Back to chat
          </Button>
          <Button asChild variant="secondary" className="gap-2">
            <a href="/api/metrics/export" target="_blank" rel="noreferrer">
              <Download className="h-4 w-4" />
              Export CSV
            </a>
          </Button>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader>
            <CardTitle>Total Sessions</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-semibold text-white">{aggregate?.total_sessions ?? 0}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Avg Turns</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-semibold text-white">{aggregate ? aggregate.average_turns.toFixed(1) : "0.0"}</p>
            <p className="text-xs text-slate-400">Messages per session</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Retrieval Latency</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-semibold text-white">
              {aggregate ? `${aggregate.average_retrieval_latency_ms.toFixed(0)} ms` : "—"}
            </p>
            <p className="text-xs text-slate-400">Average across sessions</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex items-center justify-between">
            <CardTitle>Positive Feedback</CardTitle>
            <TrendingUp className="h-4 w-4 text-emerald-400" />
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-semibold text-white">
              {aggregate?.positive_feedback_ratio !== undefined && aggregate?.positive_feedback_ratio !== null
                ? `${Math.round(aggregate.positive_feedback_ratio * 100)}%`
                : "—"}
            </p>
            <p className="text-xs text-slate-400">Of sessions with feedback</p>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 lg:grid-cols-[1fr,1.3fr]">
        <Card>
          <CardHeader>
            <CardTitle>Sessions</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            {sessionsQuery.isLoading && <p className="text-slate-400">Loading sessions...</p>}
            {sessionsQuery.data?.length === 0 && <p className="text-slate-500">No sessions recorded yet.</p>}
            {sessionsQuery.data?.map((session) => (
              <button
                key={session}
                onClick={() => setSelectedSession(session === selectedSession ? null : session)}
                className={`w-full rounded-lg border px-3 py-2 text-left transition ${
                  session === selectedSession ? "border-primary text-white" : "border-slate-800 text-slate-300 hover:border-slate-700"
                }`}
              >
                <p className="font-mono text-xs">{session}</p>
                {session === selectedSession && (
                  <p className="text-[10px] uppercase text-primary">Selected</p>
                )}
              </button>
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Session Detail</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4 text-sm">
            {!selectedSession && <p className="text-slate-400">Select a session to inspect metrics.</p>}
            {selectedSession && sessionMetricsQuery.isLoading && <p className="text-slate-400">Loading session metrics...</p>}
            {sessionMetrics && (
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-slate-400">Turns</span>
                  <span className="font-semibold text-white">{sessionMetrics.turn_count}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-slate-400">Retrieval latency</span>
                  <span className="font-semibold text-white">{sessionMetrics.retrieval_latency_ms.toFixed(0)} ms</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-slate-400">LLM latency</span>
                  <span className="font-semibold text-white">{sessionMetrics.llm_latency_ms.toFixed(0)} ms</span>
                </div>
                <div>
                  <p className="text-slate-400">Recommended products</p>
                  <ul className="mt-1 list-disc space-y-1 pl-4 text-slate-200">
                    {sessionMetrics.recommended_products.map((sku) => (
                      <li key={sku}>
                        <span className="font-mono text-xs uppercase text-slate-400">SKU</span> {sku}
                      </li>
                    ))}
                  </ul>
                </div>
                <div>
                  <p className="text-slate-400">Feedback</p>
                  <div className="mt-1 flex gap-2 text-xs text-slate-300">
                    <span>👍 {Object.values(sessionMetrics.user_feedback).filter((value) => value === "positive").length}</span>
                    <span>👎 {Object.values(sessionMetrics.user_feedback).filter((value) => value === "negative").length}</span>
                  </div>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default MetricsDashboard;
