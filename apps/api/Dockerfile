# syntax = docker/dockerfile:1

# Adjust NODE_VERSION as desired
ARG NODE_VERSION=20.19.0
FROM node:${NODE_VERSION}-slim AS base

LABEL fly_launch_runtime="Node.js"

# Node.js app lives here
WORKDIR /app

# Set production environment
ENV NODE_ENV="production"


# Throw-away build stage to reduce size of final image
FROM base AS build

# Install packages needed to build node modules
RUN apt-get update -qq && \
    apt-get install --no-install-recommends -y build-essential node-gyp pkg-config python-is-python3

# Install node modules
COPY package-lock.json package.json .npmrc ./
RUN npm ci

# Copy Prisma schema and generate client
COPY prisma ./prisma
# Use local prisma (not npx which downloads latest version)
RUN ./node_modules/.bin/prisma generate

# Copy only required application files to reduce build context
COPY src ./src
COPY railway.toml ./
COPY tsconfig.json ./



# Final stage for app image
FROM base

# Install runtime dependencies including npm/npx, Python, and uv
RUN apt-get update -qq && \
    apt-get install --no-install-recommends -y \
    ca-certificates \
    python3 \
    python3-pip \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user early
RUN useradd -m -s /bin/bash appuser

# Install uv for the appuser
USER appuser
RUN curl -LsSf https://astral.sh/uv/install.sh | sh \
    && echo 'export PATH="/home/appuser/.cargo/bin:$PATH"' >> /home/appuser/.bashrc

# Set PATH to include uv
ENV PATH="/home/appuser/.cargo/bin:$PATH"

# Switch back to root for copying files
USER root

# Copy built application with correct ownership (avoid slow recursive chown)
COPY --chown=appuser:appuser --from=build /app /app

# Switch to non-root user
USER appuser

# Start the server by default, this can be overwritten at runtime
EXPOSE 3000
CMD [ "npm", "run", "start" ]
