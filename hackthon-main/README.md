This is a [Next.js](https://nextjs.org) project bootstrapped with [`create-next-app`](https://nextjs.org/docs/app/api-reference/cli/create-next-app).

## Getting Started

First, run the development server:

```bash
npm run dev
# or
yarn dev
# or
pnpm dev
# or
bun dev
```

Open [http://localhost:3000](http://localhost:3000) with your browser to see the result.

You can start editing the page by modifying `app/page.tsx`. The page auto-updates as you edit the file.

This project uses [`next/font`](https://nextjs.org/docs/app/building-your-application/optimizing/fonts) to automatically optimize and load [Geist](https://vercel.com/font), a new font family for Vercel.

## AI Assistant Setup

The "Ask AI Assistant" panel (dashboard home, `/dashboard/assistant`) calls the real Claude API through a server route at `src/app/api/assistant/route.ts` — it's not scripted/canned.

1. Copy `.env.local.example` to `.env.local`.
2. Add your key: `ANTHROPIC_API_KEY=sk-ant-...` (get one at https://console.anthropic.com/settings/keys).
3. Restart `npm run dev`.

Without a key set, the panel still works but shows a message explaining it isn't connected yet instead of crashing. The route defaults to `claude-haiku-4-5-20251001` for fast, cheap responses — change the `model` field in `route.ts` if you want a different model. Each request sends a short summary of the traveler's current trips (from `localStorage`) as context, so the assistant can answer things like "what can I do if my flight is delayed?" with awareness of their actual itinerary.

## Learn More

To learn more about Next.js, take a look at the following resources:

- [Next.js Documentation](https://nextjs.org/docs) - learn about Next.js features and API.
- [Learn Next.js](https://nextjs.org/learn) - an interactive Next.js tutorial.

You can check out [the Next.js GitHub repository](https://github.com/vercel/next.js) - your feedback and contributions are welcome!

## Deploy on Vercel

The easiest way to deploy your Next.js app is to use the [Vercel Platform](https://vercel.com/new?utm_medium=default-template&filter=next.js&utm_source=create-next-app&utm_campaign=create-next-app-readme) from the creators of Next.js.

Check out our [Next.js deployment documentation](https://nextjs.org/docs/app/building-your-application/deploying) for more details.
#