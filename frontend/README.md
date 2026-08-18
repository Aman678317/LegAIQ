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

## Learn More

To learn more about Next.js, take a look at the following resources:

- [Next.js Documentation](https://nextjs.org/docs) - learn about Next.js features and API.
- [Learn Next.js](https://nextjs.org/learn) - an interactive Next.js tutorial.

You can check out [the Next.js GitHub repository](https://github.com/vercel/next.js) - your feedback and contributions are welcome!

## Deploy on Vercel

The easiest way to deploy your Next.js frontend is using [Vercel](https://vercel.com).

### Deployment Settings in Vercel:
- **Framework Preset**: Next.js
- **Root Directory**: `frontend` (if deploying from the root repository)
- **Build Command**: `next build`
- **Output Directory**: `.next`

### Environment Variables required in Vercel:
1. `NEXT_PUBLIC_APP_URL` — e.g. `https://your-app.vercel.app`
2. `NEXT_PUBLIC_API_URL` — e.g. `https://jurisiva-api.onrender.com/api/v1`
3. `NEXT_PUBLIC_SUPABASE_URL` — e.g. `https://xyzcompany.supabase.co`
4. `NEXT_PUBLIC_SUPABASE_ANON_KEY` — Your Supabase anonymous public key

See the full [Vercel Deployment Guide](../VERCEL_DEPLOYMENT.md) for detailed steps, CORS configuration, and Supabase Auth setup.

