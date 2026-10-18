FROM node:20-alpine

WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm install

# Build application
COPY . .
RUN mkdir -p public

ENV NEXT_TELEMETRY_DISABLED=1
ARG NEXT_PUBLIC_API_URL=""
ARG API_INTERNAL_URL="http://127.0.0.1:8000"
ARG API_PROXY_TARGET="http://backend:8000"
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
ENV API_INTERNAL_URL=$API_INTERNAL_URL
ENV API_PROXY_TARGET=$API_PROXY_TARGET

RUN npm run build

EXPOSE 3000
CMD ["npm", "start"]
