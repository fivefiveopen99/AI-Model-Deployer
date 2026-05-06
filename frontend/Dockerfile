# Build stage
FROM node:18-alpine as build-stage

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .
RUN npm run build

# Production stage
FROM nginx:alpine as production-stage

COPY --from=build-stage /app/dist /usr/share/nginx/html

# Copy nginx config with increased upload size and WebSocket support
RUN echo 'server { \
    listen 80; \
    resolver 127.0.0.11 valid=10s ipv6=off; \
    set $backend http://backend:8000; \
    client_max_body_size 10G; \
    location / { \
        root /usr/share/nginx/html; \
        index index.html; \
        try_files $uri $uri/ /index.html; \
    } \
    location /api { \
        proxy_pass $backend; \
        proxy_set_header Host $host; \
        proxy_set_header X-Real-IP $remote_addr; \
        client_max_body_size 10G; \
        proxy_connect_timeout 60s; \
        proxy_send_timeout 900s; \
        proxy_read_timeout 900s; \
        send_timeout 900s; \
    } \
    location /api/v1/ws { \
        proxy_pass $backend; \
        proxy_http_version 1.1; \
        proxy_set_header Upgrade $http_upgrade; \
        proxy_set_header Connection "upgrade"; \
        proxy_set_header Host $host; \
        proxy_set_header X-Real-IP $remote_addr; \
        proxy_read_timeout 86400; \
    } \
}' > /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
