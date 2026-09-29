# Deployment Guide

How to put this app on the internet for free, with no server of your own and no
billing card.

The two halves need different hosts, because the backend cannot run as a
serverless function: it holds an embedded Qdrant store on local disk and builds
a vector index at boot, which a stateless function cannot do.

| | Host | Card required | Cost |
|---|---|---|---|
| Frontend | **Vercel** | No | ₹0 |
| Backend | **Render Free** | No | ₹0 — charging is structurally impossible without a card |
| Backend (alt) | Google Cloud Run | Yes | ₹0 within the free tier |

> **Why Render and not Cloud Run.** Cloud Run is the better experience (wakes in
> 1–2 s), but Google requires a billing account to enable Cloud Run and Cloud
> Build at all. Render's free tier needs no card, and Render's own FAQ states
> that without a payment method it *disables* services rather than billing them
> — so there is no path by which money can be deducted. The trade-off is that a
> free instance idles out after 15 minutes and the next request waits about a
> minute while it wakes and rebuilds its index.

---

## 1. Backend → Render

`render.yaml` is a Render Blueprint, so this is one click.

1. <https://render.com> → **Get Started** → **Sign in with GitHub** (no card).
2. **New** → **Blueprint** → select `adityawadibhasme00-dot/vedalex`.
3. Render reads `render.yaml` and provisions two services:
   - `vedalex-api` — the backend. This is the one you need.
   - `vedalex-web` — a Render-hosted frontend. You do not need this if the
     frontend is on Vercel; suspend it so it does not hold an instance.
4. **Apply**. The first build takes 4–6 minutes.

### Add the LLM key

Secrets do not belong in a repo, so this is set by hand. In the dashboard go to
**vedalex-api → Environment → Add**:

```
GEMINI_API_KEY     = <your key from https://aistudio.google.com/apikey>
IPSAKTI_LLM_MODEL  = gemini-3.5-flash
```

Saving triggers an automatic redeploy (~3 min).

`GEMINI_API_KEY` is read from the process environment, **not** from a `.env`
file, so putting it in `backend/.env` has no effect.

### Get the URL

**vedalex-api → Overview** shows `https://vedalex-api.onrender.com`. You need
this for the frontend's `BACKEND_URL`.

---

## 2. Frontend → Vercel

1. <https://vercel.com> → **Add New** → **Project** → import the repo.
2. Set:

   | Setting | Value |
   |---|---|
   | Framework preset | Next.js (auto-detected) |
   | **Root Directory** | `frontend` |
   | Build command | `npm run build` (default) |
   | Start command | `npx next start` (default) |

3. **Settings → Environment Variables** → add:

   ```
   BACKEND_URL = https://vedalex-api.onrender.com
   ```

4. **Deploy**, then **Redeploy** after adding the variable.

The app calls the API through the relative path `/api/v1`, which
`next.config.js` proxies server-side to `BACKEND_URL`. Because the proxy runs on
Vercel's servers, the browser only ever talks to the Vercel origin — there is no
CORS to configure and the backend URL is never exposed to the client.

---

## 3. Verify

```bash
curl https://vedalex-api.onrender.com/api/v1/health
```

Expect `{"status":"ok", ...}` with `rag` reporting `qdrant=available` and a
non-zero document count. If `qdrant` is `missing`, the index did not build — see
Troubleshooting in the README.

Then load the Vercel URL, sign in, and ask the copilot a question. The first
answer after an idle period pays the wake-up cost; subsequent ones are fast.

---

## Why the API runs in "lite" mode

The full stack needs ~10.7 GB of model weights (`BAAI/bge-m3` plus the reranker)
and `torch`, which no free tier can host. So the deploy installs
`backend/requirements-slim.txt` — the same dependencies minus that ML stack —
and sets `IPSAKTI_USE_BGE_M3=0` / `IPSAKTI_USE_RERANKER=0`, which keeps the app
on its local hashing embedder (192-dim) + BM25 path. Everything works; semantic
answer quality is a little lower than a local run with the real models.

Measured for this configuration: **183 MB peak RAM** (the container is given
512 MB), a **4 s** index build, and a **~6 s** cold start. No compiler is needed
— every slim dependency ships a prebuilt `manylinux` wheel, which is why
`backend/Dockerfile.lite` skips `build-essential`.

### The index rebuilds itself

Free-tier disks are wiped on every restart, so `backend/scripts/serve.py` builds
the index in-process *before* the server accepts requests, and skips the rebuild
when the store already has data. It runs in the same process as the API on
purpose: the embedded Qdrant client locks its storage folder, so splitting the
build into a separate step makes the API silently fall back to an in-memory store.

### What "free" costs you

The Vercel frontend is always live and instant. The Render *backend* sleeps
after ~15 minutes idle, so the first API call after a pause takes about a minute
while it wakes and rebuilds its index — the page itself still loads instantly
from Vercel. Open the site a minute before a demo so the backend is already
awake. `BACKEND_API_KEY_SECRET` is generated for you, which is what keeps
sessions valid across restarts.

---

## Alternative: Google Cloud Run

Use this if you are willing to attach a billing account. It wakes in 1–2 s
instead of about a minute, and it is the better demo experience.

```bash
gcloud auth login
gcloud auth application-default login
gcloud services enable run.googleapis.com cloudbuild.googleapis.com
```

```bash
cd backend
cp cloudrun.env.yaml.example cloudrun.env.yaml
# edit it: the rotated GEMINI_API_KEY, a one-time BACKEND_API_KEY_SECRET, and
# CORS_ORIGINS set to your Vercel URL
```

```bash
gcloud run deploy vedalex-api \
  --source . \
  --dockerfile Dockerfile.lite \
  --region asia-south1 \
  --allow-unauthenticated \
  --memory 512Mi --cpu 1 \
  --concurrency 1 \
  --timeout 300 \
  --min-instances 0 \
  --max-instances 2 \
  --env-vars-file cloudrun.env.yaml
```

```bash
gcloud run services describe vedalex-api --region asia-south1 --format "value(status.url)"
```

**What each flag is doing.** `Dockerfile.lite` installs `requirements-slim.txt`
and runs `scripts/serve.py`. `--min-instances 0` is required to stay on the free
tier — a warm instance is billed, and that is the single easiest way to incur a
charge. `--concurrency 1` matters because the embedded Qdrant client holds a lock
on its storage folder: one request per instance keeps that unambiguous and avoids
two instances racing to build the same index. `--timeout 300` is safe on the free
tier because Cloud Run only bills for time a request is actually being served.

**Cost.** Cloud Run's free tier is 2 million requests, 180,000 vCPU-seconds and
360,000 GiB-seconds of memory per month. A demo with a few hundred requests uses
well under 0.1% of that, so the bill is ₹0. New accounts also receive a $300
credit. To be safe, set a budget alert in the Google Cloud console.

**Not verified locally:** the image was never built on the author's machine,
because Docker is not installed there. Wheel availability and the build context
were checked directly instead; the first build happens on Cloud Build.
