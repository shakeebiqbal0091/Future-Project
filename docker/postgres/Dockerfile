# PostgreSQL Dockerfile for AI Agent Orchestration Platform
FROM postgres:15-alpine

# Set environment variables
ENV POSTGRES_DB=ai_orchestration
ENV POSTGRES_USER=postgres
ENV POSTGRES_PASSWORD=postgres

# Copy initialization scripts
COPY ./init.sql /docker-entrypoint-initdb.d/init.sql

# Expose port
EXPOSE 5432

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
  CMD pg_isready -U postgres -d ai_orchestration || exit 1