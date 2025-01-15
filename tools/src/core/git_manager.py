import os
import git
from utils.logger import logger

class GitManager:
    def __init__(self):
        # Get the root directory (parent of tools directory)
        current_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        root_dir = os.path.dirname(current_dir)
        self.repo = git.Repo(root_dir)
        
    def has_changes(self):
        return bool(self.repo.index.diff(None) or self.repo.untracked_files)
    
    def commit_and_push(self, message):
        try:
            # Add all changes
            self.repo.git.add('.')
            
            # Commit changes
            self.repo.index.commit(message)
            
            # Push to remote
            origin = self.repo.remote('origin')
            origin.push()
            
            logger.info("Successfully committed and pushed changes")
            return True
        except Exception as e:
            logger.error(f"Error in git operations: {e}")
            return False 