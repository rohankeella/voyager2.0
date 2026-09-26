import { NextRequest, NextResponse } from "next/server";

export const runtime = "nodejs";

type ChatMessage = { role: "user" | "assistant"; content: string };

const SYSTEM_PROMPT = `You are the Voyager travel assistant, built into a personalized tour-planning app.
You help travelers plan trips, compare destinations, estimate budgets, adapt itineraries around
disruptions (weather, delays, cancellations), and answer questions about their booked trips.

Keep replies short and conversational (2-5 sentences unless the user asks for a list or itinerary).
Use ₹ (INR) for prices unless the user asks otherwise. If you don't have enough information about
their specific trip to answer precisely, say so and ask one clarifying question rather than guessing.
If asked to make a change to a live booking, describe what you'd change and note that an operator or
the itinerary screen would need to confirm it — you don't have direct write access.`;

const GEMINI_MODEL = process.env.GEMINI_MODEL || "gemini-2.5-flash";

export async function POST(req: NextRequest) {
  let body: { message?: string; history?: ChatMessage[]; context?: string };
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ reply: "That request didn't come through right — try sending your message again." });
  }

  const message = (body.message ?? "").trim();
  if (!message) {
    return NextResponse.json({ reply: "Ask me anything about your trip — planning, pricing, or last-minute changes." });
  }

  const apiKey = process.env.GEMINI_API_KEY;
  if (!apiKey) {
    return NextResponse.json({
      reply:
        "The AI assistant isn't connected yet. Add a GEMINI_API_KEY to your .env.local file (get one free at https://aistudio.google.com/apikey) and restart the dev server.",
      configured: false,
    });
  }

  const history = Array.isArray(body.history) ? body.history.slice(-10) : [];
  const systemText = body.context ? `${SYSTEM_PROMPT}\n\nCurrent traveler context:\n${body.context}` : SYSTEM_PROMPT;

  const contents = [
    ...history
      .filter((m) => m.role === "user" || m.role === "assistant")
      .map((m) => ({
        role: m.role === "assistant" ? "model" : "user",
        parts: [{ text: m.content }],
      })),
    { role: "user", parts: [{ text: message }] },
  ];

  try {
    const url = `https://generativelanguage.googleapis.com/v1beta/models/${encodeURIComponent(
      GEMINI_MODEL,
    )}:generateContent`;
    const res = await fetch(url, {
      method: "POST",
      headers: {
        "content-type": "application/json",
        "x-goog-api-key": apiKey,
      },
      body: JSON.stringify({
        systemInstruction: { parts: [{ text: systemText }] },
        contents,
        generationConfig: { maxOutputTokens: 500, temperature: 0.7 },
      }),
    });

    if (!res.ok) {
      const errBody = await res.text();
      console.error("Gemini API error", res.status, errBody);
      const reply =
        res.status === 400
          ? "The assistant request was rejected by Gemini — the API may have changed or your key is malformed."
          : res.status === 401 || res.status === 403
            ? "The assistant couldn't authenticate with Gemini — double-check your GEMINI_API_KEY at https://aistudio.google.com/apikey."
            : res.status === 429
              ? "Gemini free-tier rate limit hit (15 req/min) — wait a few seconds and try again."
              : "The assistant hit an error reaching Gemini just now. Please try again in a moment.";
      return NextResponse.json({ reply, configured: true, error: true });
    }

    const data = await res.json();
    const parts = data?.candidates?.[0]?.content?.parts;
    const text = Array.isArray(parts)
      ? parts
          .map((p: { text?: string }) => p?.text ?? "")
          .filter(Boolean)
          .join("\n")
      : "";

    return NextResponse.json({ reply: text || "I didn't get a response back — try asking again.", configured: true });
  } catch (err) {
    console.error("Assistant route network error", err);
    return NextResponse.json({
      reply: "Couldn't reach the assistant right now — check your connection and try again.",
      configured: true,
      error: true,
    });
  }
}
