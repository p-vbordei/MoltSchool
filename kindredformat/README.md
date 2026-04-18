# kindredformat.org

Static site that publishes the KAF (Kindred Artifact Format) 0.1 spec.

**Live:** https://kindredformat-production.up.railway.app
(DNS cutover to `kindredformat.org` pending.)

## Structure

- `content/` — authoritative markdown files (spec, examples, implementers guide).
- `src/app/` — Next.js 15 app-router pages that render the markdown at build time.
- `next.config.mjs` — configured for `output: "export"` so `npm run build` produces a static `out/` directory.

## Develop

```bash
cd kindredformat
npm install
npm run dev      # http://localhost:3100
```

## Build static site

```bash
npm run build    # writes ./out/
```

`./out/` is deploy-ready for any static host (Vercel, Cloudflare Pages,
Netlify, S3 + CloudFront). The Railway deployment uses a minimal
`Dockerfile` that runs `serve -s out -l $PORT` on top of the built
output — see [`../docs/deployment.md`](../docs/deployment.md).

## Editing the spec

Edit the markdown files in `content/`. The site rebuilds on the next
`npm run build`. The spec is the source of truth — the site is just a
viewer.
