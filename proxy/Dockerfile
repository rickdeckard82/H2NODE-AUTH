FROM nginx:1.27-alpine

RUN apk add --no-cache openssl

COPY nginx.conf /etc/nginx/templates/default.conf.template
COPY entrypoint.sh /docker-entrypoint.d/40-h2node-tls.sh
RUN chmod +x /docker-entrypoint.d/40-h2node-tls.sh

EXPOSE 80 443
