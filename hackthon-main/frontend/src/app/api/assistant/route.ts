import { NextRequest, NextResponse } from "next/server";

export const runtime = "nodejs";

export async function POST(req: NextRequest) {
  let body: unknown;
  try {
    const raw = await req.text();
    if (raw.length > 60000) return NextResponse.json({ reply: "Please shorten your message or conversation.", error: true }, { status: 413 });
    body = JSON.parse(raw);
  } catch {
    return NextResponse.json({ reply: "Invalid message. Please try again.", error: true }, { status: 400 });
  }
  const base = (process.env.BACKEND_API_URL || process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000").replace(/\/+$/, "");
  try {
    const response = await fetch(`${base}/api/assistant`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(body),
      signal: AbortSignal.timeout(50000),
      cache: "no-store",
    });
    const data = await response.json();
    if (typeof data?.reply !== "string") {
      return NextResponse.json({ reply: response.status === 422 ? "Please send a shorter, non-empty message with valid conversation history." : "The assistant returned an invalid response. Please try again.", error: true }, { status: response.status === 422 ? 422 : 502 });
    }
    return NextResponse.json({ reply: data.reply, configured: data.configured, error: data.error }, { status: response.status });
  } catch {
    return NextResponse.json({ reply: "The assistant is temporarily unreachable. Please try again.", error: true }, { status: 502 });
  }
}
