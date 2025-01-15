from typing import Dict, List
from models.content_types import Content
from utils.logger import logger
from core.gpt_service import GPTService

class ContentMerger:
    def __init__(self, readme_path: str, gpt_service: GPTService):
        self.readme_path = readme_path
        self.gpt_service = gpt_service
        
    def merge_content(self, new_sections: Dict[str, List[Content]]) -> bool:
        """Merge new content into existing README using LLM."""
        try:
            current_content = self._read_current_content()
            
            # Let GPT handle the merging section by section
            for section_name, items in new_sections.items():
                current_content = self._merge_section(
                    current_content,
                    section_name,
                    items
                )
            
            self._write_content(current_content)
            return True
        except Exception as e:
            logger.error(f"Failed to merge content: {e}")
            return False
    
    def _merge_section(self, content: str, section_name: str, new_items: List[Content]) -> str:
        """Merge a single section using GPT."""
        try:
            # Extract existing section content if it exists
            section_start = content.find(f"## {section_name}")
            if section_start == -1:
                # Create new section if it doesn't exist
                return content + f"\n\n## {section_name}\n\n" + self._format_items(new_items)
            
            # Find section end
            next_section = content.find("\n## ", section_start + 1)
            section_end = next_section if next_section != -1 else len(content)
            
            # Extract and merge section content
            section_content = content[section_start:section_end]
            merged_content = self.gpt_service.merge_content(section_content, new_items)
            
            # Replace old section with merged content
            return content[:section_start] + merged_content + content[section_end:]
            
        except Exception as e:
            logger.error(f"Failed to merge section {section_name}: {e}")
            return content
    
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
    
    @staticmethod
    def _format_items(items: List[Content]) -> str:
        """Format content items as markdown."""
        return "\n".join([
            f"- [{item.title}]({item.url}): {item.description}"
            for item in items
        ]) 