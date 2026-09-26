"use client";

import { useState, useRef, useEffect } from "react";
import { Sparkles, Send, AlertCircle } from "lucide-react";
import { aiSuggestedPrompts } from "@/lib/dashboard-data";
import { loadTrips } from "@/lib/trip-storage";
import { cn } from "@/lib/utils";

type Message = { role: "user" | "assistant"; text: string; isError?: boolean };

function buildTripContext(): string {
  try {
    const trips = loadTrips().filter((t) => t.destination);
    if (trips.length === 0) return "The traveler hasn't created any trips yet.";
    return trips
      .slice(0, 5)
      .map((t) => {
        const days = t.days.length > 0 ? `, ${t.days.length} day itinerary drafted` : "";
        return `- ${t.name || t.destination} to ${t.destination} (${t.startDate || "dates TBD"} to ${
          t.endDate || "TBD"
        }), ${t.travelers} traveler(s), budget tier: ${t.budget || "not set"}, status: ${t.status ?? "draft"}${days}.`;
      })
      .join("\n");
  } catch {
    return "";
  }
}

export default function AIAssistantPanel() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isThinking, setIsThinking] = useState(false);
  const [notConfigured, setNotConfigured] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, isThinking]);

  const send = async (text: string) => {
    const trimmed = text.trim();
    if (!trimmed || isThinking) return;

    const nextMessages: Message[] = [...messages, { role: "user", text: trimmed }];
    setMessages(nextMessages);
    setInput("");
    setIsThinking(true);

    try {
      const res = await fetch("/api/assistant", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          message: trimmed,
          history: nextMessages.map((m) => ({ role: m.role, content: m.text })),
          context: buildTripContext(),
        }),
      });
      const data: { reply: string; configured?: boolean; error?: boolean } = await res.json();
      setNotConfigured(data.configured === false);
      setMessages((prev) => [...prev, { role: "assistant", text: data.reply, isError: !!data.error }]);
    } catch {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", text: "Couldn't reach the assistant — check your connection and try again.", isError: true },
      ]);
    } finally {
      setIsThinking(false);
    }
  };

  return (
    <div className="flex flex-col rounded-3xl border border-gray-100 bg-white p-5 shadow-sm">
      <div className="flex items-center gap-2">
        <span className="flex h-8 w-8 items-center justify-center rounded-full bg-primary/10 text-primary">
          <Sparkles className="h-4 w-4" />
        </span>
        <div>
          <h3 className="text-sm font-bold text-dark">Ask AI Assistant</h3>
          <p className="text-xs text-gray-500">Planning, changes, recommendations & more</p>
        </div>
      </div>

      {notConfigured && (
        <div className="mt-3 flex items-start gap-2 rounded-2xl bg-amber-50 p-3 text-xs text-amber-700">
          <AlertCircle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
          <span>
            Not connected yet — add <code className="font-mono">GEMINI_API_KEY</code> to{" "}
            <code className="font-mono">.env.local</code> (free at{" "}
            <a
              href="https://aistudio.google.com/apikey"
              target="_blank"
              rel="noreferrer"
              className="underline hover:text-amber-900"
            >
              aistudio.google.com/apikey
            </a>
            ) and restart the dev server.
          </span>
        </div>
      )}

      {messages.length > 0 && (
        <div ref={scrollRef} className="mt-4 max-h-64 space-y-3 overflow-y-auto pr-1">
          {messages.map((m, i) => (
            <div
              key={i}
              className={cn(
                "max-w-[90%] whitespace-pre-wrap rounded-2xl px-3.5 py-2 text-sm",
                m.role === "user"
                  ? "ml-auto bg-primary text-white"
                  : m.isError
                    ? "bg-red-50 text-red-600"
                    : "bg-gray-50 text-gray-700"
              )}
            >
              {m.text}
            </div>
          ))}
          {isThinking && (
            <div className="max-w-[90%] rounded-2xl bg-gray-50 px-3.5 py-2 text-sm text-gray-400">Thinking…</div>
          )}
        </div>
      )}

      <div className="mt-4 flex flex-wrap gap-2">
        {aiSuggestedPrompts.map((prompt) => (
          <button
            key={prompt}
            onClick={() => send(prompt)}
            disabled={isThinking}
            className="rounded-full border border-gray-200 px-3 py-1.5 text-left text-xs font-medium text-gray-600 transition-colors hover:border-primary hover:text-primary disabled:opacity-50"
          >
            {prompt}
          </button>
        ))}
      </div>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          send(input);
        }}
        className="mt-4 flex items-center gap-2"
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          type="text"
          placeholder="Ask anything…"
          className="flex-1 rounded-full border border-gray-200 bg-gray-50 px-4 py-2.5 text-sm text-dark placeholder:text-gray-400 focus:border-primary focus:bg-white focus:outline-none focus:ring-2 focus:ring-primary/20"
        />
        <button
          type="submit"
          disabled={isThinking}
          className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-primary text-white transition-colors hover:bg-primary/90 disabled:opacity-50"
          aria-label="Send"
        >
          <Send className="h-4 w-4" />
        </button>
      </form>
    </div>
  );
}
