# Experiences

Scope: `/experiences` and `/experience/[id]`. Mode: Operate. Travelers search and compare actual catalog activities, then inspect provider details. Preserve the existing landing page, teal identity, Geist typography and Next.js navigation.

## Direction contract

THESIS: Make catalog search understandable, keeping unavailable commercial claims visibly absent.

OWN-WORLD: Inherit Voyager teal (#0f766e), Geist, pale green-neutral backgrounds, dark readable text, thin dividers, 13px card corners and consistent Lucide icons.

STORY: Search a destination or activity, refine by actual catalog categories, compare prices in their supplied currency, inspect details and continue to a supplied provider link.

FIRST VIEWPORT: Voyager navigation, back control, compact page title, full-width search, horizontal categories, breadcrumbs, 238px sidebar and three-column desktop results. Mobile stacks search controls and moves filters into a native modal drawer.

FORM: User-prescribed travel catalog structure; no concept seed needed for this specified composition in an established visual world. No screenshot was included in the attachments.

FINISH: Verify desktop/mobile composition, API filter behavior, error/empty states and keyboard operation; preserve the incumbent system. Backend images only, with honest missing-photo placeholders; no generated assets or fabricated ratings.

## Implementation comparison and verification

Compared with `PRODUCT.md`, `src/app/globals.css`, the root layout and the direction contract above on 2026-09-27:

- Identity stays Voyager. Primary actions, active categories and keyboard outlines use the incumbent teal (`#0f766e`); text inherits the root Geist font. The page-scoped pale green background (`#f7faf9`), dark text (`#172c2a`), white surfaces, thin dividers and 13px cards follow this surface's existing brief without replacing global tokens.
- Search and catalog remain the first task. The desktop capture has a sidebar and three result columns; the 768px capture has two columns and a Filters control; the 390px capture has one column and stacked search controls. Detail content and the visit panel stack below 800px. Shared non-landing navigation now collapses below `xl`, resolving the review's tablet clipping finding; the landing navigation retains its existing breakpoint.
- Inspected evidence: [desktop](review/experiences/desktop.png), [tablet](review/experiences/tablet.png), [mobile](review/experiences/mobile.png), and [desktop detail](review/experiences/desktop-detail.png), [tablet detail](review/experiences/tablet-detail.png), [mobile detail](review/experiences/mobile-detail.png). The detail captures show the teal focus outline and explicit unavailable-booking state. These are development captures and include the Next.js development indicator.
- Catalog imagery uses supplied HTTPS provider URLs; missing or failed images show “Photo not provided.” No raster assets were generated or independently sourced. Supplied prices retain their currency; ratings, discounts and commercial benefits appear only when the corresponding catalog fields support them. Missing detail copy and booking links remain visibly unavailable.
- The implementation owner reports passing production build, API checks and browser flow checks. This documentation pass verified source consistency and the six captured compositions; it did not rerun those checks. The independent reviewer's final disposition is **ship**: its single tablet-navigation finding was scored resolved in the recaptured tablet listing and detail screenshots.

`DESIGN.md` was already absent. The incumbent implementation and product constraints remain the comparison authority; this ordinary extension does not create a replacement global design system or repair unrelated documentation drift. Only this surface brief was updated by the documentation pass.
