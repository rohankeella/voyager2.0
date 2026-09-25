"use client";

import { useState, useRef, useEffect } from "react";
import { Sparkles, Send, Bot, User as UserIcon, Loader2, AlertCircle } from "lucide-react";
import { agentsApi, ApiError, type PlanTripResponse } from "@/lib/api";
import { cn } from "@/lib/utils";

type ChatMessage =
  | { role: "user"; text: string }
  | { role: "assistant"; text: string; kind?: "info" | "success" | "error"; trace?: PlanTripResponse["trace"] };

type Props = {
  samplePrompts: string[];
  onPlan: (res: PlanTripResponse & { prompt: string }) => void;
  hasPlan: boolean;
};

export default function CopilotChat({ samplePrompts, onPlan, hasPlan }: Props) {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      role: "assistant",
      text: "Hi — tell me where and when you want to travel. Include your budget, home city, and anything you love (art, food, hikes). I'll plan the whole DAG.",
      kind: "info",
    },
  ]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [statusReady, setStatusReady] = useState<boolean | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    agentsApi
      .status()
      .then((s) => {
        setStatusReady(s.gemini_configured);
        if (!s.gemini_configured) {
          setMessages((prev) => [
            ...prev,
            {
              role: "assistant",
              kind: "error",
              text:
                "Planner Agent isn't connected. Add GEMINI_API_KEY to backend/.env " +
                "(free at https://aistudio.google.com/apikey) and restart the backend.",
            },
          ]);
        }
      })
      .catch(() => setStatusReady(false));
  }, []);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, busy]);

  const send = async (text: string) => {
    const goal = text.trim();
    if (!goal || busy) return;

    setMessages((prev) => [...prev, { role: "user", text: goal }]);
    setInput("");
    setBusy(true);

    try {
      const res = await agentsApi.planTrip({ user_goal: goal, persist: true, max_iterations: 3 });

      if (!res.trip) {
        const errs = res.errors.length > 0 ? res.errors.slice(0, 3).join(" · ") : "no plan produced";
        setMessages((prev) => [
          ...prev,
          {
            role: "assistant",
            kind: "error",
            text: `I couldn't produce a valid plan (${res.iterations} attempts): ${errs}`,
            trace: res.trace,
          },
        ]);
        return;
      }

      const nodeCount = res.trip.nodes.length;
      const totalCost = res.trip.nodes.reduce((s, n) => s + n.financials.cost_usd, 0);
      const budget = res.trip.global_constraints.max_budget_usd;
      const hitl = res.hitl_required;

      const summary =
        `Planned ${nodeCount} nodes for ${res.trip.global_constraints.home_location ?? "your trip"}, ` +
        `$${totalCost.toFixed(0)} of $${budget.toFixed(0)} budget` +
        (res.persisted_id ? ` · saved as ${res.persisted_id}` : " · not saved (sign in to save)") +
        (hitl ? " · review card on the right needs your approval." : ".");

      setMessages((prev) => [
        ...prev,
        { role: "assistant", kind: "success", text: summary, trace: res.trace },
      ]);

      onPlan({ ...res, prompt: goal });
    } catch (e) {
      let msg = "Something went wrong reaching the Planner.";
      if (e instanceof ApiError) msg = e.message;
      else if (e instanceof Error) msg = e.message;
      setMessages((prev) => [...prev, { role: "assistant", kind: "error", text: msg }]);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex h-full flex-col rounded-3xl border border-gray-100 bg-white shadow-sm">
      {/* header */}
      <div className="flex items-center gap-2 border-b border-gray-100 p-4">
        <span className="flex h-8 w-8 items-center justify-center rounded-full bg-primary/10 text-primary">
          <Sparkles className="h-4 w-4" />
        </span>
        <div className="flex-1">
          <h3 className="text-sm font-bold text-dark">AI Co-Pilot</h3>
          <p className="text-[11px] text-gray-500">
            {statusReady === null
              ? "Checking Planner Agent…"
              : statusReady
                ? "Planner · Executor · Supervisor ready"
                : "Planner Agent offline — see backend/.env"}
          </p>
        </div>
      </div>

      {/* messages */}
      <div ref={scrollRef} className="flex-1 space-y-3 overflow-y-auto p-4">
        {messages.map((m, i) => (
          <MessageBubble key={i} message={m} />
        ))}
        {busy && (
          <div className="flex items-center gap-2 text-xs text-gray-500">
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
            <span>Planning… (Planner → Executor → Supervisor)</span>
          </div>
        )}
      </div>

      {/* sample prompts */}
      {!hasPlan && !busy && (
        <div className="flex flex-wrap gap-2 border-t border-gray-100 p-3">
          {samplePrompts.map((p) => (
            <button
              key={p}
              onClick={() => send(p)}
              disabled={busy || statusReady === false}
              className="max-w-full truncate rounded-full border border-gray-200 px-3 py-1.5 text-left text-[11px] font-medium text-gray-600 transition-colors hover:border-primary hover:text-primary disabled:opacity-40"
              title={p}
            >
              {p}
            </button>
          ))}
        </div>
      )}

      {/* input */}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          send(input);
        }}
        className="flex items-center gap-2 border-t border-gray-100 p-3"
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          type="text"
          placeholder="Describe your ideal trip…"
          disabled={busy || statusReady === false}
          className="flex-1 rounded-full border border-gray-200 bg-gray-50 px-4 py-2.5 text-sm text-dark placeholder:text-gray-400 focus:border-primary focus:bg-white focus:outline-none focus:ring-2 focus:ring-primary/20 disabled:opacity-50"
        />
        <button
          type="submit"
          disabled={busy || !input.trim() || statusReady === false}
          className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-primary text-white transition-colors hover:bg-primary/90 disabled:opacity-40"
          aria-label="Send"
        >
          {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
        </button>
      </form>
    </div>
  );
}

function MessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === "user";
  const Icon = isUser ? UserIcon : Bot;

  const bubbleClass = isUser
    ? "ml-auto bg-primary text-white"
    : message.kind === "error"
      ? "bg-red-50 text-red-700 border border-red-100"
      : message.kind === "success"
        ? "bg-emerald-50 text-emerald-800 border border-emerald-100"
        : "bg-gray-50 text-gray-700";

  return (
    <div className={cn("flex items-start gap-2", isUser && "flex-row-reverse")}>
      <span
        className={cn(
          "flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-white",
          isUser ? "bg-primary" : "bg-gray-400",
        )}
      >
        <Icon className="h-3.5 w-3.5" />
      </span>
      <div className={cn("max-w-[85%] whitespace-pre-wrap rounded-2xl px-3.5 py-2 text-sm", bubbleClass)}>
        {message.role === "assistant" && message.kind === "error" && (
          <AlertCircle className="mb-1 inline h-3.5 w-3.5" />
        )}
        {message.text}
        {message.role === "assistant" && message.trace && message.trace.length > 0 && (
          <details className="mt-2 text-[11px] opacity-80">
            <summary className="cursor-pointer">Agent trace ({message.trace.length} steps)</summary>
            <ul className="mt-1 space-y-0.5 pl-4">
              {message.trace.map((t, i) => (
                <li key={i} className="list-disc">
                  {String(t.agent ?? "agent")}
                  {typeof t.iteration === "number" ? ` · iter ${t.iteration}` : ""}
                  {typeof t.nodes_processed === "number" ? ` · ${t.nodes_processed} nodes` : ""}
                  {typeof t.errors_count === "number" ? ` · ${t.errors_count} errors` : ""}
                </li>
              ))}
            </ul>
          </details>
        )}
      </div>
    </div>
  );
}
