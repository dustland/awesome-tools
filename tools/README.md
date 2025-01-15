# Awesome Embodied AI - Automation Tools 🛠️

This directory contains the automation tools and utilities for maintaining and updating the Awesome Embodied AI list.

## 🚀 Features

- Automated content curation from various sources
- GitHub integration for updates and maintenance
- Content validation and formatting
- Automated PR generation for updates

## 📋 Prerequisites

- Python 3.8+
- Poetry for dependency management
- GitHub API access token (for GitHub integration)

## 🔧 Installation

1. Install Poetry (if not already installed):

```bash
curl -sSL https://install.python-poetry.org | python3 -
```

2. Install dependencies:

```bash
poetry install
```

3. Set up environment variables:

```bash
cp .env.example .env
```

4. Configure your `.env` file with the required credentials:

```env
GITHUB_TOKEN=your_github_token
# Add other required environment variables
```

## 💻 Usage

### Running the Content Update Tool

```bash
poetry run python src/main.py
```

### Available Commands

- Update content: `poetry run python src/main.py update`
- Validate content: `poetry run python src/main.py validate`
- Generate PR: `poetry run python src/main.py pr`

## 📁 Project Structure

```
tools/
├── src/                    # Source code
│   ├── core/              # Core functionality
│   │   ├── github_client.py   # GitHub API integration
│   │   ├── content_merger.py  # Content merging logic
│   │   ├── gpt_service.py     # GPT integration
│   │   └── git_manager.py     # Git operations
│   ├── utils/             # Utility functions
│   │   ├── logger.py      # Logging configuration
│   │   └── config.py      # Configuration management
│   ├── models/            # Data models
│   │   └── content_types.py   # Content type definitions
│   └── main.py           # Entry point
├── tests/                # Test suite
├── config/               # Configuration files
│   └── config.yaml      # Main configuration
├── pyproject.toml       # Poetry configuration
└── .env.example         # Environment variables template
```

## 🧪 Testing

Run the test suite:

```bash
poetry run pytest
```

## 🤝 Contributing

1. Ensure you have all prerequisites installed
2. Create a new branch for your feature
3. Write tests for new functionality
4. Run the test suite
5. Submit a pull request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](../LICENSE) file for details.
