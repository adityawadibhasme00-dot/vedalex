# Deep Dive 4 — Frontend Routes and UX

`frontend/src/app` (5 routes), `frontend/src/lib` (9 modules)

## Route map

```
src/app/page.tsx                              landing
src/app/dashboard/page.tsx                    the working surface
src/app/innovation-lab/page.tsx               agent catalogue
src/app/innovation-lab/agents/[slug]/page.tsx one agent, input form + run
src/app/login/page.tsx                        auth
```

Five routes is a deliberate constraint. Every additional top-level screen is a
place a compliance user can get lost, and the product's value is that a
formulation leads to a *decision*, not that there is a lot to explore. The
Innovation Lab is nested rather than promoted to a top-level tab because it is
the exploration surface, not the primary workflow.

## The main loop

The dashboard is a **single passport workspace**, not a collection of
independent tools. `lib/api.ts` is the whole client, and the shape of its
functions is the shape of the product:

```
intake        → createPassportFromIntake
                ↓
assessment    → evaluateAssessment          (deterministic rule engine)
                ↓
provenance    → getProvenanceGraph          (why this classification)
                ↓
what-if       → simulateWhatIf               (change one thing, re-evaluate)
                ↓
red team      → challengeInnovation          (attack your own case)
                ↓
evidence      → getEvidenceGaps              (what is missing)
                ↓
handoff       → dispatchExpertHandoff        (give it to a human)
```

Each step is a separate endpoint with its own type, so the UI cannot conflate
"this is a risk finding" with "this is a requirement" or "this is a missing
fact". That separation mirrors the backend's separation of classification,
evidence and explanation, and it is what keeps the interface from turning into a
wall of undifferentiated AI output.

## API boundary

```ts
const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || '/api/v1';
```

Browser calls go to the **same origin** (`/api/v1`) and are proxied
server-side to the backend container. No backend hostname is exposed to the
client, so there is nothing to leak and no CORS preflight in the hot path. In
compose this is `NEXT_PUBLIC_API_BASE_URL=/api/v1` plus
`BACKEND_URL=http://backend:8000` as a build arg.

## Cross-cutting concerns

| Module | Responsibility |
| --- | --- |
| `AuthContext.tsx` | session, token, role |
| `LangContext.tsx` + `i18n.ts` | interface language |
| `AccessibilityContext.tsx` | motion / a11y preferences |
| `offlineStorage.ts` | local draft survival |
| `RootSync.tsx` | app-shell synchronisation |
| `exportManager.ts` | client-side export |
| `innolabApi.ts` + `agentBlurbs.ts` | agent catalogue |

`offlineStorage.ts` is the one that matters most for this domain. A
pharmacist or patent agent may lose connectivity mid-assessment; losing typed
formulation detail because a request failed is unacceptable. Drafts persist
locally and reconcile on reconnect.

`agentBlurbs.ts` and `innolabApi.ts` are split from the generic `api.ts`
because the agent catalogue is metadata, not workflow — it is static enough to
not warrant the same treatment as a passport mutation.

## Trust is a UI concern

The backend does the hard part — the gate, the verification table, the audit
trail. The frontend's obligation is to **surface** it rather than summarise it
away:

- Findings render with their citation, not as a bare badge.
- The verification table is the answer's companion, not a debug view.
- "Removed by verification" is stated plainly. Silently returning a shorter
  answer teaches users that the tool is unreliable; showing what was cut and
  why is what makes it auditable.
- `escalation/` exists as a component group because handing a case to a human
  is a first-class outcome, not an error state.

## Current state

`npm run typecheck` — clean.
`npm run lint` — no errors; three warnings, all pre-existing and none in files
touched by the scaling work:

- `innovation-lab/agents/[slug]/page.tsx:289` — `useCallback` missing
  `collectInputs` in deps
- `components/landing/HerbShowcase.tsx:173` — raw `<img>` instead of
  `next/image`
- `components/ThreeBackground.tsx:156` — ref read in effect cleanup

## Known gaps

- No error boundary per route; a throw in a dashboard panel takes down the
  whole workspace view.
- No loading state for the multi-second `/assessment/evaluate` and
  `/rag/ask` calls beyond a spinner — a progress affordance would matter, since
  these are the calls that run the full pipeline.
- Long agent runs (now available as background jobs) have no client-side
  polling surface yet; the `/jobs` endpoints exist and are admin-gated.
- The three lint warnings above are unfixed.
- No route-level code splitting concerns, but `ThreeBackground` is loaded on
  the landing route and carries a WebGL cost.
