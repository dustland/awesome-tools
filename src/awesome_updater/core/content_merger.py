from typing import Dict, List, Any
import os
import re
from utils.logger import logger
from awesome_updater.core.gpt_service import GPTService

class ContentMerger:
    def __init__(self, readme_path: str, gpt_service: GPTService):
        # Ensure we're targeting the root README.md, not the tools one
        self.readme_path = os.path.abspath(readme_path)
        if os.path.basename(os.path.dirname(self.readme_path)) == "tools":
            raise ValueError("README path should point to root README.md, not tools/README.md")
        self.gpt_service = gpt_service
        self.sections = {
            'foundation_models': '## Foundation Models & World Models',
            'perception': '## Perception & Understanding',
            'learning': '## Learning & Control',
            'simulation': '## Simulation & Environments',
            'hardware': '## Hardware & Platforms',
            'datasets': '## Datasets & Benchmarks',
            'companies': '## Companies & Research Labs'
        }
        
    def merge_content(self, new_content: str) -> bool:
        """Merge new content into existing README."""
        try:
            # Read existing content
            with open(self.readme_path, 'r', encoding='utf-8') as f:
                current_content = f.read()

            # Organize new content by section
            organized_content = self._organize_content(new_content)
            
            # Update each section
            updated_content = current_content
            for section, content in organized_content.items():
                updated_content = self._update_section(updated_content, section, content)

            # Write back if changed
            if updated_content != current_content:
                with open(self.readme_path, 'w', encoding='utf-8') as f:
                    f.write(updated_content)
                return True
                
            return False

        except Exception as e:
            logger.error(f"Error merging content: {str(e)}")
            return False
    
    def _organize_content(self, content: str) -> Dict[str, List[str]]:
        # Use GPT to categorize content into sections
        prompt = f"""
        Categorize the following content into appropriate sections:
        {content}
        
        Sections:
        - Foundation Models & World Models
        - Perception & Understanding
        - Learning & Control
        - Simulation & Environments
        - Hardware & Platforms
        - Datasets & Benchmarks
        - Companies & Research Labs
        
        Return the categorized content in a structured format.
        """
        
        categorized_content = self.gpt_service.categorize_content(prompt)
        return categorized_content

    def _update_section(self, content: str, section: str, new_items: List[str]) -> str:
        section_header = self.sections[section]
        section_pattern = f"{section_header}.*?(?=##|$)"
        
        # Find section
        section_match = re.search(section_pattern, content, re.DOTALL)
        if not section_match:
            # Section doesn't exist, add it
            return f"{content}\n\n{section_header}\n{''.join(new_items)}"
            
        # Update existing section
        section_content = section_match.group(0)
        updated_section = f"{section_header}\n{''.join(new_items)}"
        return content.replace(section_content, updated_section) 