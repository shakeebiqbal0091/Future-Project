# Redis Dockerfile for AI Agent Orchestration Platform
FROM redis:7-alpine

# Set configuration
COPY redis.conf /usr/local/etc/redis/redis.conf

# Expose port
EXPOSE 6379

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
  CMD redis-cli ping || exit 1

# Default command
CMD ["redis-server", "/usr/local/etc/redis/redis.conf"]