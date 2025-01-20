# Awesome Embodied AI Tools

This directory contains automation tools for maintaining and updating the Awesome Embodied AI list.

## Overview

These tools automatically curate and update the main Awesome Embodied AI list by:

- Searching for new relevant content using Tavily API
- Fetching GitHub metrics and research papers
- Merging new content into the main README.md
- Posting daily news updates to X/Twitter

## Components

- `src/main.py` - Main script for content updates
- `src/post_news.py` - Script for posting news to X/Twitter
- `src/core/`
  - `content_fetcher.py` - Fetches content from various sources
  - `content_merger.py` - Merges new content into README
  - `gpt_service.py` - Uses GPT-4 for content curation
  - `git_manager.py` - Handles Git operations
  - `news_poster.py` - Handles news posting to X/Twitter

## Setup

1. Copy `.env.example` to `.env` and fill in your API keys:

   - GitHub token
   - OpenAI API key
   - Tavily API key
   - Twitter API keys (for news posting)

2. Install dependencies:

```bash
poetry install
```

## Usage

Run content update:

```bash
poetry run python src/main.py
```

Post news to X/Twitter:

```bash
poetry run python src/post_news.py
```

## Deployment

The tools are configured to run automatically on Railway:

- Content updates run daily at midnight Shanghai time
- News posts run daily at 9 AM Shanghai time

## Contributing

Please read the main CONTRIBUTING.md file in the root directory for guidelines.
