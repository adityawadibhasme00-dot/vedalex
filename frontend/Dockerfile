FROM node:20-alpine AS builder

# BACKEND_URL is baked into the Next.js rewrites at build time. Inside the
# Docker network the backend is reachable at its service name (http://backend:8000);
# for local builds it defaults to http://localhost:8000.
ARG BACKEND_URL=http://localhost:8000
ENV BACKEND_URL=$BACKEND_URL
ARG NEXT_PUBLIC_API_BASE_URL=/api/v1
ENV NEXT_PUBLIC_API_BASE_URL=$NEXT_PUBLIC_API_BASE_URL

WORKDIR /app

COPY package.json ./
RUN npm install

COPY . .
RUN npm run build

FROM node:20-alpine AS runner
WORKDIR /app

ENV NODE_ENV=production

COPY --from=builder /app/package.json ./
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/public ./public

EXPOSE 3000

CMD ["npm", "run", "start"]
