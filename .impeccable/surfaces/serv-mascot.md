# Serv mascot: existing home and customer chat

## Overview

Serv is the user-approved continuation of the V-Chat Mic prototype in the existing VFServ application. It introduces the assistant on `/` and identifies it in the `/chat` header. This is a local addition to the incumbent blue, white and near-black interface. `PRODUCT.md` remains authoritative for product purpose and human responsibility for service decisions.

Root `DESIGN.md` explicitly governs `/ui-long` only. Its presentation typography, section pacing and demonstration composition do not govern these operational surfaces. This note records Serv without changing root `DESIGN.md`, `.impeccable/design.json` or shared theme tokens.

## Colors

The artwork preserves the incumbent brand blue (`#1e40af`), near-black outline (`#0f172a`) and white chat face (`#fff`). The cap uses brand blue; headset and microphone use navy (`#172554`). The approved HubHome refinement adds a stationary pale-blue circle, radial lighting centered at `50% 38%`, concentric rings and three separate twinkling stars. Its dark variant uses navy. These remain local mascot colors, not new global application tokens.

`frontend/src/app/theme.css` remains the source for application surfaces:

| Role | Light | Dark |
| --- | --- | --- |
| Page | `#f6f7f9` | `#0f1115` |
| Surface | `#fff` | `#171b22` |
| Raised surface | `#f1f5f9` | `#222833` |
| Divider | `#e2e8f0` | `#465264` |
| Text | `#0f172a` | `#e7ebf2` |
| Muted text | `#64748b` | `#a0abbc` |

Serv's speech bubble uses `--theme-surface`, `--theme-text` and `--theme-line`; the SVG keeps its white face and blue identity across themes. The existing application theme adapters continue to own surrounding controls, message bubbles and panels.

## Typography

The existing application font and hierarchy remain in place. Home retains the bold, tightly spaced support question (`text-3xl`, desktop `38px`) and its blue emphasized phrase. Serv's centered bubble text is `14px`, weight `600`, line-height `1.55`; up to `800px` it is `13px`. Compact chat speech is `12px`. Chat retains its title, metadata and message text; agent labels read “Serv”.

## Layout

Home places the mascot above the support heading and existing prompt box. The guest introduction/login pill was removed at the user's request; the signed-in customer greeting remains available. The approved refinement reduces character and decorative geometry by 10%, preserving speech font size for readability:

| Viewport | Character | Wrapper height | Circle core / outer ring diameter | Bubble placement |
| --- | --- | --- | --- | --- |
| Above `800px` | `122.472px` | `189px` | `162px` / `198px` | Right, `260px` wide, top `22.5px` |
| Up to `800px` | `122.472px` | `216px` | `138.6px` / `174.6px` | Below, top `159.3px` |
| Up to `600px` | `102.06px` | `199.8px` | `118.8px` / `154.8px` | Below, top `138.6px` |

Below `800px`, bubble width is capped at `300px` and inset from available width. Its notch points toward Serv.

Chat preserves `48px` button hit areas (`42px` up to `600px`) and scales only its SVG artwork by `.9`. Circle cores are `47.8px` and `40.6px`, respectively, with `2px` and `4px` concentric rings. Its `230px` speech bubble sits below the character and appears on hover, focus-within, or hello, wink, surprise, tap and listen states. History, feed, input, privacy text and mobile controls retain their existing layout responsibilities. Magnifying glass, tablet and response card remain mirrored onto viewer-left using `translate(200 0) scale(-1 1)`.

## Elevation & Depth

The stationary hero circle uses a radial gradient, `9px` and `18px` ring shadows, and a subtle ambient shadow. It does not pulse. The speech bubble has a fine theme border, `16px` corners, a small directional notch and a soft local shadow (`0 12px 28px -15px rgb(15 23 42 / .28)`). The existing home prompt border, focus ring, rounded panels and chat surface separation remain the visual structure.

## Shapes

The character uses a white speech-shaped face, thick near-black outline, rounded limbs, blue cap and navy headset. The button has a `12px` focus shape with a visible `2px` outline and `3px` offset. Illustration geometry is defined once in `ServArtwork.tsx` for both sizes.

## Components

`frontend/src/features/shared/components/serv/ServMascot.tsx` owns interaction and localized speech, `ServMascot.module.css` owns size and motion, and `ServArtwork.tsx` owns the inline SVG. `LandingPage.tsx` connects the real home textarea. `CustomerChatContainer.tsx` connects the chat textarea through `ChatInputBar.tsx` and derives the mascot status from current application state. `ChatFeed.tsx` and `ChatMessageItem.tsx` use the Serv name consistently.

Caret tracking mirrors real input typography, width, padding, borders, wrapping and scrolling. It follows the active endpoint of a selection: `selectionStart` for backward selections, otherwise `selectionEnd`. Focus, input, selection, keyboard, scrolling, resize and composition completion update the gaze. While the input is focused, pointer movement cannot replace caret gaze. Outside editing, non-touch pointer movement can guide the eyes.

| Application evidence | Serv behavior |
| --- | --- |
| Input focused or edited | Listening; gaze follows the real caret |
| Actual chat request pending | Thinking; after `2200ms`, waiting with magnifying glass |
| Image upload pending | Reading with tablet |
| Agent response after the initial greeting | Presenting the response card; returns after `3200ms` |
| Critical notice, upload/safety error, guest limit or error message | Care; tap reactions cannot override it |
| Greeting or tap while unlocked | Short greeting/expression sequence, then restore |

Waiting props depend on actual pending state. The response card means a response is available, not that a repair succeeded or service was dispatched. Errors take precedence over upload, request and response poses. Product notices and messages remain the substantive source of guidance.

Vietnamese and English speech, button labels and titles follow the existing locale context. Both variants render the localized `data-serv-speech` text; compact visibility follows the states above. The SVG is decorative (`aria-hidden`); the surrounding native button has a localized accessible name and keyboard focus. Speech has no pointer events and does not intercept input.

The hero's three decorative SVG stars twinkle separately over `3.6s`, staggered by `0`, `1.2s` and `2.4s`. This adapts the inspected HubHome pattern of a stationary circle and independently animated stars to VFServ blue/navy. Under `prefers-reduced-motion: reduce`, stars remain static, continuous CSS animation and gaze transitions are absent, and idle expression cycling is skipped. When the mascot leaves the viewport or the document is hidden, its CSS animations pause, including the stars. Caret updates are gated when offscreen. Event listeners, timers, observer, animation frame and temporary caret mirror are cleaned up on effect teardown.

## Do's and Don'ts

- Do preserve the existing application shell, blue identity and text/input hierarchy when extending Serv.
- Do use the shared artwork and actual request state for both surfaces.
- Do keep pointer gaze subordinate to active typing, including wrapped text and backward selection.
- Do retain reduced-motion behavior, localized accessible controls and offscreen animation pausing.
- Don't present a mascot reaction as a service decision, diagnosis, dispatch or successful repair.
- Don't promote this local surface note into a replacement identity or apply `/ui-long` composition to home/chat.

## Evidence and existing documentation drift

Inspected `PRODUCT.md`, `DESIGN.md`, `.impeccable/design.json`, `frontend/src/app/theme.css`, all three Serv source files, the five integration files and `frontend/e2e/serv-mascot.spec.ts`.

Visually inspected `.impeccable/review/serv-home-width-1440.png`, `serv-home-width-375.png`, `serv-chat-width-1440.png`, `serv-chat-width-375.png` and `serv-home-1595.png`. Home retains centered support heading, prompt, suggestions and emergency contact below Serv; narrow text wraps within the page. Chat retains the desktop history column and compact mobile header/feed/input arrangement. The wide home image confirms the resting greeting and character placement; the test screenshots show listening and an explicitly simulated response. Screenshots provide static layout evidence, not proof of real service operation.

For the latest 10% size reduction and separate sparkle refinement, the implementing agent reports nine passing E2E checks across `375`, `768` and `1440px`, and live computed geometry and animation timing verification. Earlier halo/bubble assertions passed at all three viewports, with a reviewer verdict of ship within that scope. Earlier verification recorded 33 passing unit tests and a successful production build before these visual refinements; the subsequent source build compiled with full route-generation output pending at that report. Behavior checks use mocked APIs; local backend history fetch is unavailable. This documentation pass inspected current source without rerunning tests. The backward-selection correction remains in the active-endpoint calculation and regression assertion. No Vercel deployment was performed.

Existing sidecar preview/source drift is outside this change: the `/ui-long` workspace preview uses local `var(--paper,#fff)` and `var(--ink,#0f172a)` fallbacks without reproducing that page's scoped dark token context. It therefore cannot independently represent the page's dark workspace from the global application theme alone. Both system files are currently untracked, so Git provides no committed baseline for their earlier state. Their `/ui-long` scope and narrative remain intact; neither was regenerated or repaired for Serv.

Chat-only refinement: compact Serv hides arm, feet and ground groups at the user's request, preserving the face, cap, headset, microphone and eye behavior. Home keeps the complete character. Verified rendered display rules and screenshots at1440/390px.

Compact chat refinement: the circular halo is hidden; the home halo remains visible.

Compact chat header: no mascot speech box or native speech tooltip; symbolic listening bubble hidden. Avatar button is 44px at every breakpoint, inside a vertically centered 57px header. The home speech box remains available. Verified at1440/390px.

Additional home-only size refinement: artwork reduced another 10% to122.472px desktop /102.06px mobile. Halo, speech and compact chat sizing remain unchanged.

Home artwork reduced a further10% to122.472px desktop /102.06px mobile; chat sizing unchanged.

Cap refinement: preserve the approved blue and white V, use a three-quarter crown with visible panel seams and a curved brim projecting forward toward viewer-right, following the supplied baseball-cap reference.

Brim refinement: shorten the visor tip and reduce its depth with a continuous crown attachment, keeping crown, color, direction and white V unchanged.
