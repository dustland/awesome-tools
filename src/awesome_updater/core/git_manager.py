import os
import git
import tempfile
from datetime import datetime
from utils.logger import logger

class GitManager:
    def __init__(self, repo_path=None, target_repo_url=None):
        if repo_path:
            self.repo = git.Repo(repo_path)
            logger.info(f"Initialized git manager with local repo at: {repo_path}")
        elif target_repo_url:
            self.target_repo_url = target_repo_url
            self.temp_dir = tempfile.mkdtemp()
            logger.info(f"Created temporary directory for cloning: {self.temp_dir}")
            
            # Clone the target repository
            try:
                logger.info(f"Cloning repository from {target_repo_url}...")
                self.repo = git.Repo.clone_from(
                    self.target_repo_url, 
                    self.temp_dir,
                    env={"GIT_ASKPASS": "echo", "GIT_USERNAME": os.getenv("GITHUB_USERNAME"), "GIT_PASSWORD": os.getenv("GITHUB_TOKEN")}
                )
                latest_commit = self.repo.head.commit
                logger.info(f"Successfully cloned repository:")
                logger.info(f"  - Latest commit: {latest_commit.hexsha[:8]}")
                logger.info(f"  - Author: {latest_commit.author}")
                logger.info(f"  - Date: {datetime.fromtimestamp(latest_commit.committed_date)}")
                logger.info(f"  - Message: {latest_commit.message.strip()}")
            except Exception as e:
                logger.error(f"Error cloning repository: {str(e)}")
                if hasattr(self, 'temp_dir') and os.path.exists(self.temp_dir):
                    import shutil
                    shutil.rmtree(self.temp_dir)
                    logger.info("Cleaned up temporary directory after failed clone")
                raise
        else:
            raise ValueError("Either repo_path or target_repo_url must be provided")
        
    def __del__(self):
        """Cleanup temporary directory when object is destroyed"""
        import shutil
        try:
            if hasattr(self, 'temp_dir') and os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
                logger.info(f"Cleaned up temporary directory: {self.temp_dir}")
        except Exception as e:
            logger.error(f"Error cleaning up temporary directory: {str(e)}")

    def get_readme_path(self) -> str:
        """Get the path to README.md in the cloned repository"""
        if hasattr(self, 'temp_dir'):
            path = os.path.join(self.temp_dir, "README.md")
        else:
            path = os.path.join(self.repo.working_dir, "README.md")
        logger.debug(f"README.md path: {path}")
        return path
        
    def has_changes(self) -> bool:
        """Check if there are any changes in the repository"""
        has_unstaged = bool(self.repo.index.diff(None))
        has_staged = bool(self.repo.index.diff('HEAD'))
        has_untracked = bool(self.repo.untracked_files)
        
        logger.info("Git status:")
        logger.info(f"  - Unstaged changes: {has_unstaged}")
        logger.info(f"  - Staged changes: {has_staged}")
        logger.info(f"  - Untracked files: {has_untracked}")
        
        return has_unstaged or has_staged or has_untracked
        
    def commit_and_push(self, message: str = "Update README.md"):
        """Commit and push changes to the repository."""
        try:
            if not self.has_changes():
                logger.info("No changes to commit")
                return False
                
            # Add changes
            if hasattr(self, 'temp_dir'):
                logger.info("Adding README.md to staging area...")
                self.repo.index.add(['README.md'])
            else:
                logger.info("Adding all changes to staging area...")
                self.repo.git.add('.')
            
            # Commit changes
            logger.info(f"Creating commit with message: {message}")
            commit = self.repo.index.commit(message)
            logger.info(f"Created commit: {commit.hexsha[:8]}")
            
            # Push changes
            logger.info("Pushing changes to remote repository...")
            if hasattr(self, 'temp_dir'):
                self.repo.git.push('origin', 'main')
                logger.info("Successfully pushed to origin/main")
            else:
                origin = self.repo.remote(name='origin')
                push_info = origin.push()
                for info in push_info:
                    logger.info(f"Pushed to {info.remote_ref_string}")
            
            logger.info("Git operations completed successfully")
            return True
        except Exception as e:
            logger.error(f"Error in git operations: {str(e)}")
            raise