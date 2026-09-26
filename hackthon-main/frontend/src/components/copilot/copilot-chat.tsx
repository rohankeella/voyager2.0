"use client";

import { useState, useRef, useEffect } from "react";
import { Sparkles, ArrowUp, ArrowRight, Loader2, AlertCircle } from "lucide-react";
import { agentsApi, ApiError, type PlanTripResponse } from "@/lib/api";
import { cn } from "@/lib/utils";

type ChatMessage =
  | { role: "user"; text: string }
  | { role: "assistant"; text: string; kind?: "info" | "success" | "error"; trace?: PlanTripResponse["trace"] };

type Props = {
  samplePrompts: string[];
  onPlan: (res: PlanTripResponse & { prompt: string }) => void;
  onBusyChange?: (busy: boolean) => void;
  hasPlan: boolean;
};

export default function CopilotChat({ samplePrompts, onPlan, onBusyChange, hasPlan }: Props) {
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
        setStatusReady(s.groq_configured);
        if (!s.groq_configured) {
          setMessages((prev) => [
            ...prev,
            {
              role: "assistant",
              kind: "error",
              text:
                "The trip planner is temporarily unavailable. Please contact the site owner or try again later.",
            },
          ]);
        }
      })
      .catch(() => setStatusReady(false));
  }, []);

  useEffect(() => {
    onBusyChange?.(busy);
  }, [busy, onBusyChange]);

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
        `Planned ${nodeCount} nodes for ${res.trip.global_constraints.destination ?? "your trip"}, ` +
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

  const unavailable = statusReady === false;

  return (
    <div className="flex h-full flex-col overflow-hidden rounded-2xl border border-slate-200/80 bg-white">
      {/* header */}
      <div className="flex shrink-0 items-center gap-2.5 border-b border-slate-100 px-4 py-3">
        <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/10 text-primary">
          <Sparkles className="h-4 w-4" />
        </span>
        <div className="min-w-0 flex-1">
          <h2 className="text-sm font-semibold text-slate-900">AI Co-Pilot</h2>
          <p className="flex items-center gap-1.5 text-xs text-slate-500">
            <span
              aria-hidden
              className={cn(
                "h-1.5 w-1.5 rounded-full",
                statusReady === null ? "bg-slate-300" : statusReady ? "bg-emerald-500" : "bg-red-500",
              )}
            />
            {statusReady === null
              ? "Checking Planner Agent…"
              : statusReady
                ? "Planner · Executor · Supervisor ready"
                : "Trip planner unavailable"}
          </p>
        </div>
      </div>

      {/* messages */}
      <div ref={scrollRef} className="min-h-0 flex-1 space-y-3 overflow-y-auto px-4 py-4" aria-live="polite">
        {messages.map((m, i) => (
          <MessageBubble key={i} message={m} />
        ))}
        {busy && (
          <div className="flex max-w-[92%] items-start gap-2.5 rounded-2xl rounded-bl-md bg-slate-100 px-3.5 py-2.5 text-sm text-slate-700">
            <Loader2 className="mt-0.5 h-4 w-4 shrink-0 animate-spin text-primary" />
            <div>
              <div className="font-medium text-slate-900">Planning your trip…</div>
              <div className="mt-0.5 text-xs text-slate-500">
                Planner → Executor → Supervisor. This usually takes under a minute.
              </div>
            </div>
          </div>
        )}
      </div>

      {/* sample prompts */}
      {!hasPlan && !busy && (
        <div className="shrink-0 border-t border-slate-100 px-3 pb-1 pt-3">
          <div className="px-1 pb-1.5 text-xs font-medium text-slate-500">Try one of these</div>
          <ul className="space-y-1">
            {samplePrompts.map((p) => (
              <li key={p}>
                <button
                  type="button"
                  onClick={() => send(p)}
                  disabled={busy || unavailable}
                  className="group flex w-full items-start gap-2 rounded-lg px-2 py-1.5 text-left text-xs leading-snug text-slate-600 transition-colors duration-150 hover:bg-primary/5 hover:text-primary focus-visible:bg-primary/5 focus-visible:text-primary focus-visible:outline-none disabled:pointer-events-none disabled:opacity-50"
                >
                  <ArrowRight className="mt-px h-3.5 w-3.5 shrink-0 text-slate-400 transition-colors duration-150 group-hover:text-primary" />
                  <span>{p}</span>
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* input */}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          send(input);
        }}
        className="shrink-0 p-3"
      >
        <div className="flex items-center gap-2 rounded-xl border border-slate-200 bg-slate-50 p-1.5 pl-3.5 transition-colors duration-150 focus-within:border-primary focus-within:bg-white focus-within:ring-2 focus-within:ring-primary/15">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            type="text"
            aria-label="Describe your trip"
            placeholder="Describe your ideal trip…"
            disabled={busy || unavailable}
            className="min-w-0 flex-1 bg-transparent text-sm text-slate-900 placeholder:text-slate-500 focus:outline-none disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={busy || !input.trim() || unavailable}
            className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary text-white transition-colors duration-150 hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40 focus-visible:ring-offset-1 disabled:bg-slate-300"
            aria-label="Send"
          >
            {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <ArrowUp className="h-4 w-4" />}
          </button>
        </div>
      </form>
    </div>
  );
}

function MessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === "user";

  const bubbleClass = isUser
    ? "ml-auto rounded-br-md bg-primary text-white"
    : message.kind === "error"
      ? "rounded-bl-md bg-red-50 text-red-800"
      : message.kind === "success"
        ? "rounded-bl-md bg-teal-50 text-teal-950"
        : "rounded-bl-md bg-slate-100 text-slate-700";

  return (
    <div className={cn("w-fit max-w-[92%] whitespace-pre-wrap rounded-2xl px-3.5 py-2.5 text-sm leading-relaxed", bubbleClass)}>
      {message.role === "assistant" && message.kind === "error" && (
        <AlertCircle className="mr-1 inline h-3.5 w-3.5 -translate-y-px" />
      )}
      {message.text}
      {message.role === "assistant" && message.trace && message.trace.length > 0 && (
        <details className="mt-2 text-xs text-teal-900/80">
          <summary className="cursor-pointer select-none rounded focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40">
            Agent trace ({message.trace.length} steps)
          </summary>
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
  );
}
