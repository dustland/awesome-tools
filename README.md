# Awesome Embodied AI Tools

This repository contains the tools used to maintain and update the [Awesome Embodied AI](https://github.com/dustland/awesome-embodied-ai) list.

## Overview

These tools automatically curate and update the main Awesome Embodied AI list by:

- Searching for new relevant content using Tavily API
- Fetching GitHub metrics and research papers
- Merging new content into the main README.md
- Posting daily news updates to X/Twitter

## Project Structure

```
src/
├── awesome_updater/    # Awesome list content updater
│   ├── core/          # Core functionality specific to awesome_updater
│   │   ├── content_fetcher.py
│   │   ├── content_merger.py
│   │   ├── git_manager.py
│   │   ├── github_client.py
│   │   └── gpt_service.py
│   └── main.py
├── news_poster/       # News posting tool
│   ├── main.py
│   └── news_poster.py
├── models/           # Shared data models and schemas
└── utils/           # Shared utility functions and helpers
```

## Getting Started

### Prerequisites

- Python 3.11 or higher
- [Poetry](https://python-poetry.org/) for dependency management
- GitHub account with API access
- OpenAI API key
- Tavily API key

### Installation

1. Clone the repository:

```bash
git clone https://github.com/dustland/awesome-tools.git
cd awesome-tools
```

2. Install dependencies using Poetry:

```bash
poetry install
```

3. Set up environment variables:

```bash
cp .env.example .env
```

Edit `.env` file and fill in your API keys and configuration:

- `GITHUB_TOKEN`: Your GitHub API token
- `OPENAI_API_KEY`: Your OpenAI API key
- `TAVILY_API_KEY`: Your Tavily API key
- `GITHUB_USERNAME`: Your GitHub username
- `GITHUB_EMAIL`: Your GitHub email

### Running the Tools

#### Content Updater

The content updater tool searches for new content and updates the Awesome Embodied AI list. Run it with either:

```bash
# Using the script command
poetry run awesome_updater
```

This will:

1. Search for new relevant content using Tavily API
2. Fetch GitHub metrics and research papers
3. Use GPT to evaluate and format new content
4. Update the main README.md file
5. Create a pull request with the changes

#### Automated Updates (Railway.app)

The tool is configured to run automatically on Railway.app with the following schedule:

- Content updates: Daily at midnight Shanghai time (UTC+8)
- News posting: Daily at 9 AM Shanghai time (UTC+8)

To deploy on Railway.app:

1. Create a new project
2. Connect your GitHub repository
3. Set up the required environment variables
4. The cron jobs will automatically start running based on the schedule in `railway.toml`

## Tools Description

- `awesome_updater/` - Tool for updating the README file in the Awesome Embodied AI repository
- [WIP] `news_poster/` - Tool for posting news to X/Twitter

## Setup

1. Clone the repository
2. Copy `.env.example` to `.env` and fill in the required API keys
3. Install dependencies:
   ```bash
   pip install -e .
   ```

## Usage

Each tool can be run independently from its respective directory. See individual tool documentation for specific usage instructions.

## Deployment

The tools are configured to run automatically on Railway:

- Content updates run daily at midnight Shanghai time
- News posts run daily at 9 AM Shanghai time

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT
