# --- runner stage: assumes .next/standalone and public are pre-built ---
FROM node:20-slim AS runner
WORKDIR /app
ENV NODE_ENV=production

# Copy pre-built Next.js artifacts (built locally on the host to avoid container SSL issues)
COPY public ./public
COPY .next/standalone ./
COPY .next/static ./.next/static

EXPOSE 3000
CMD ["node", "server.js"]
