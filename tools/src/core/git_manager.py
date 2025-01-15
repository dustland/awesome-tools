import git
from utils.logger import logger

class GitManager:
    def __init__(self):
        self.repo = git.Repo(".")
    
    def has_changes(self) -> bool:
        """Check if there are uncommitted changes."""
        return bool(self.repo.index.diff(None) or self.repo.untracked_files)
    
    def commit_and_push(self, message: str) -> bool:
        """Commit and push changes."""
        try:
            self.repo.index.add(["README.md"])
            self.repo.index.commit(message)
            self.repo.remote().push()
            return True
        except Exception as e:
            logger.error(f"Failed to commit and push: {e}")
            return False 