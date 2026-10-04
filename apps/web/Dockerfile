# Build context is the repo root:
#   docker build -f apps/web/Dockerfile .
# NEXT_PUBLIC_* values are baked into the client bundle at build time; they
# point at the API port as exposed on the HOST, since the browser calls it.

FROM node:20-alpine AS build
ARG NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
ARG NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws/live
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_WS_URL=$NEXT_PUBLIC_WS_URL
WORKDIR /app
COPY apps/web/package.json apps/web/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY apps/web .
RUN npm run build

FROM node:20-alpine
WORKDIR /app
ENV NODE_ENV=production
COPY --from=build /app/node_modules ./node_modules
COPY --from=build /app/package.json ./package.json
COPY --from=build /app/next.config.mjs ./next.config.mjs
COPY --from=build /app/.next ./.next
EXPOSE 3000
CMD ["node_modules/.bin/next", "start", "-p", "3000"]
