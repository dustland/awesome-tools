from typing import Dict, List, Any
import os
import re
from utils.logger import logger
from utils.gpt_service import GPTService
from awesome_updater.core.awesome_gpt_service import AwesomeGPTService

class ContentMerger:
    def __init__(self, readme_path: str, gpt_service: GPTService):
        # Ensure we're targeting the root README.md, not the tools one
        self.readme_path = os.path.abspath(readme_path)
        if os.path.basename(os.path.dirname(self.readme_path)) == "tools":
            raise ValueError("README path should point to root README.md, not tools/README.md")
            
        # Initialize specialized GPT service
        self.awesome_gpt = AwesomeGPTService(gpt_service)
        
        # Define section headers
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
        """Merge new content into the README file."""
        try:
            # Read current content
            with open(self.readme_path, 'r', encoding='utf-8') as f:
                current_content = f.read()
            
            # Merge content using specialized GPT service
            merged_content = self.awesome_gpt.merge_content(current_content, new_content)
            
            # If content was successfully merged and changed
            if merged_content and merged_content != current_content:
                # Write merged content back to file
                with open(self.readme_path, 'w', encoding='utf-8') as f:
                    f.write(merged_content)
                logger.info("Successfully merged and wrote new content")
                return True
            else:
                logger.info("No changes needed in content")
                return False
                
        except Exception as e:
            logger.error(f"Error merging content: {e}")
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