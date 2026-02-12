#!/usr/bin/env bash
# Entrypoint for Celery worker container.
set -e
exec celery -A apps.jobs.celery_app worker --loglevel=info
