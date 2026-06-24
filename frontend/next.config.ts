import type { NextConfig } from "next";
import path from "path";

const nextConfig: NextConfig = {
  // Load .env from the project root (one level above frontend/)
  // so NEXT_PUBLIC_* variables are picked up without a frontend/.env.local
  env: {},
  experimental: {},
};

// Tell Next.js to look for .env files in the repo root, not frontend/
// This is done by setting the working-directory-relative envDir.
// Next.js respects the `dotenv` resolution order from the CWD where
// `next dev` / `next build` is invoked; starting the dev server from
// the frontend/ directory with --env-file keeps a single source of truth.
export default nextConfig;
