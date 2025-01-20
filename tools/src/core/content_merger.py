from typing import Dict, List
import os
from utils.logger import logger
from core.gpt_service import GPTService

class ContentMerger:
    def __init__(self, readme_path: str, gpt_service: GPTService):
        # Ensure we're targeting the root README.md, not the tools one
        self.readme_path = os.path.abspath(readme_path)
        if os.path.basename(os.path.dirname(self.readme_path)) == "tools":
            raise ValueError("README path should point to root README.md, not tools/README.md")
        self.gpt_service = gpt_service
        
    def merge_content(self, new_content: str) -> bool:
        """Merge new content into existing README."""
        try:
            current_content = self._read_current_content()
            
            # Use GPT to merge the content
            merged_content = self.gpt_service.merge_content(current_content, new_content)
            
            # Check if content has actually changed
            if merged_content != current_content:
                logger.info("Content has been updated, writing changes...")
                self._write_content(merged_content)
                return True
            else:
                logger.info("No new content to merge")
                return False
            
        except Exception as e:
            logger.error(f"Failed to merge content: {e}")
            return False
    
    def _read_current_content(self) -> str:
        """Read current README content."""
        try:
            with open(self.readme_path, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            return ""
    
    def _write_content(self, content: str) -> None:
        """Write merged content back to README."""
        with open(self.readme_path, 'w', encoding='utf-8') as f:
            f.write(content) 