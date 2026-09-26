import AIAssistantPanel from "@/components/dashboard/ai-assistant-panel";

export default function AssistantPage() {
  return (
    <div className="mx-auto max-w-2xl">
      <h1 className="text-2xl font-bold text-dark">AI Assistant</h1>
      <p className="mt-1 text-sm text-gray-500">
        Ask about your itinerary, get recommendations, or handle changes on the go.
      </p>
      <div className="mt-6">
        <AIAssistantPanel />
      </div>
    </div>
  );
}
