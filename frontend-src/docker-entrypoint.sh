#!/bin/sh
set -e

# Replace ${PORT} in nginx.conf with the actual PORT environment variable
# Default to 8080 if PORT is not set
export PORT=${PORT:-8080}

# Use envsubst to replace ${PORT} in the template
envsubst '${PORT}' < /etc/nginx/templates/nginx.conf.template > /etc/nginx/conf.d/default.conf

# Start nginx
exec nginx -g 'daemon off;'

