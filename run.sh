#!/bin/bash

# Function to log with timestamp
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Run awesome_updater
log "Starting awesome_updater..."
if poetry run python -m awesome_updater.main; then
    log "awesome_updater completed successfully"
else
    log "awesome_updater failed with exit code $?"
fi

# Add a small delay between runs to avoid rate limits
sleep 5

# Run news_poster
log "Starting news_poster..."
if poetry run python -m news_poster.main; then
    log "news_poster completed successfully"
else
    log "news_poster failed with exit code $?"
fi 