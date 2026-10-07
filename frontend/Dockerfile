FROM node:20-alpine

WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm install

# Build application
COPY . .
RUN mkdir -p public

ENV NEXT_TELEMETRY_DISABLED=1
ARG NEXT_PUBLIC_API_URL="http://localhost:8000"
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL

RUN npm run build

EXPOSE 3000
CMD ["npm", "start"]
