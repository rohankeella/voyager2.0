# Landing surface brief

**Surface:** `/` · **Job:** Persuade · **Audience:** travelers exploring personalized trip planning.

The user requested the supplied interactive globe hero and an image corridor as the second section, using Voyager's existing copy and destination imagery. The primary action remains registration (`/register`); destination browsing (`/discover`) provides the secondary path.

## Content and composition

The hero retains “Your next journey, personalized for you” and its planning and exploration actions. “Places our travelers love” introduces the corridor; six named links beneath it lead to the existing destination detail routes. The page continues with the planning process, preference-based recommendations, a closing registration action, and footer navigation. These are existing product statements, not independently verified traveler endorsements or outcome evidence.

## Scope of visual changes

This extends the incumbent visual system. Global tokens remain in `src/app/globals.css`, and Geist remains the body font. Landing-only paper, ink, and muted colors live in `src/components/landing/landing.module.css`; the reference serif appears only as the italic hero accent. Teal actions retain the existing brand primary. The landing navbar variant preserves application routes while adding section anchors. Globe rules use the component's prefixed selectors in `src/components/ui/orbit-delivery-hero.css`.

No new global design system is established by this brief. Do not propagate the globe, corridor, hero serif, or landing palette to application screens without a separate requirement.

## Asset provenance

- Globe scene code derives from the user-supplied reference, with Voyager content and controls around it. Runtime world and courier models load from `https://cdn.jsdelivr.net/gh/fadeichev2121/planet@b3f70fbf4b577845b1d9d5947c9410fb4d925dae/`; Draco decoders load from Google's versioned decoder CDN.
- The italic font comes from the supplied reference's `cdn.21st.dev` WOFF2 URL, recorded in the landing stylesheet with a Georgia fallback.
- The corridor uses 18 distinct destination photos, split into separate nine-photo left and right sequences. Photos reuse `src/lib/mock-data.ts` destination images, requesting a smaller Unsplash width. The preference section uses its existing Unsplash landscape URL.

These are provenance records, not a license audit. Images, models, decoder resources, and the accent font retain external network dependencies.

## Controls and adaptation

The globe supports pointer dragging and focused arrow-key rotation while playing. Its button and Space key pause or resume it; pausing clears movement input. Loading text and an error boundary with a retry action are implemented. Rendering stops while offscreen or when the document is hidden.

The corridor has a separately labeled pause/play button. Repeated images are decorative and hidden from assistive technology; the named destination navigation exposes meaningful links. Landing links and buttons have visible focus outlines. The mobile navigation button exposes its expanded state.

Below 1024px the hero copy stacks above the globe, the corridor shortens, and the planning-process columns stack. The globe container is 560px tall at 760–1023px and 440px below 760px. The preference section retains two columns until it stacks below 760px. Landing desktop navigation starts at the `lg` breakpoint, retaining the menu button on tablets. Touch interaction belongs to the globe; its accessible instructions direct users to swipe outside it to scroll. Reduced-motion preference starts the globe paused, freezes corridor animations, suppresses landing CSS transitions, and sets the mobile menu's Framer Motion transition duration to zero through `useReducedMotion`.

## Evidence and limits

Source evidence: `src/app/page.tsx`, `src/components/landing/*`, `src/components/layout/navbar.tsx`, `src/components/ui/orbit-delivery-hero.jsx`, `src/components/ui/orbit-delivery-hero.css`, `src/components/ui/image-stream-hero.tsx`, and the global stylesheet/layout.

The runnable browser check is `scripts/check-landing.cjs`, covering desktop (1440px), tablet (768px), and mobile (390px). Desktop and mobile captures are present in `.impeccable/review/`. This documentation pass inspected implementation and artifact presence; it did not rerun browser checks or certify the captures. The Impeccable launcher was unavailable and its engine was not installed, so no engine report is claimed.

