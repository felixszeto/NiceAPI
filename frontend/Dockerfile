# Build stage
FROM node:20-alpine as build-stage
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build

# Production stage
FROM node:20-alpine
WORKDIR /app
COPY package*.json ./
# 只安裝生產環境依賴
RUN npm install --only=production
COPY --from=build-stage /app/dist ./dist
COPY server.js ./
EXPOSE 6670
CMD ["node", "server.js"]