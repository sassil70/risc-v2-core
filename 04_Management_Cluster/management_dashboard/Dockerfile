# RISC V2.0 - Cluster 4: Management (Next.js)
FROM node:20-slim

WORKDIR /app

# Install python and build tools for node-gyp (C++ bindings)
RUN apt-get update && apt-get install -y python3 make g++ && rm -rf /var/lib/apt/lists/*

# Copy Package Files
COPY package*.json ./

# Install Dependencies
RUN npm install

# Copy Source Code
COPY . .

# Build for production
RUN npm run build 2>/dev/null || true

# Expose Port
EXPOSE 3000

# Run Next.js (Cloud Run sets PORT env var)
CMD ["npm", "run", "start"]
