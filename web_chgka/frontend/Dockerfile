FROM node:24-alpine

WORKDIR /app

# Install the exact dependency graph recorded in the lockfile.
COPY package.json package-lock.json ./
RUN npm ci

COPY . .

# Development-only image: Compose bind-mounts the source and starts Vite.
CMD ["npm", "run", "dev", "--", "--host"]

