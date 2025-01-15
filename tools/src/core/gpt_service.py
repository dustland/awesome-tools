from typing import Dict, List, Optional
import openai
from models.content_types import Content
from utils.logger import logger
from utils.config import Config

class GPTService:
    def __init__(self, api_key: str):
        self.client = openai.OpenAI(api_key=api_key)
        self.config = Config.load_config()
    
    def analyze_readme(self, content: str) -> Dict[str, List[Content]]:
        """Analyze README content and extract relevant information."""
        try:
            response = self.client.chat.completions.create(
                model=self.config["openai"]["model"],
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert in Embodied AI and robotics, tasked with analyzing and extracting relevant content from README files."
                    },
                    {
                        "role": "user",
                        "content": self._create_analysis_prompt(content)
                    }
                ],
                temperature=self.config["openai"]["temperature"]
            )
            return self._parse_analysis_response(response.choices[0].message.content)
        except Exception as e:
            logger.error(f"Failed to analyze README: {e}")
            return {}
    
    def merge_content(self, existing_content: str, new_items: List[Content]) -> str:
        """Merge new content into existing section."""
        try:
            response = self.client.chat.completions.create(
                model=self.config["openai"]["model"],
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert curator of Embodied AI content, tasked with merging and organizing information."
                    },
                    {
                        "role": "user",
                        "content": self._create_merge_prompt(existing_content, new_items)
                    }
                ],
                temperature=self.config["openai"]["temperature"]
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Failed to merge content: {e}")
            return existing_content
    
    def _create_analysis_prompt(self, content: str) -> str:
        return f"""Analyze this README content and extract relevant information about Embodied AI and robotics:

{content}

Focus on:
1. Projects and tools
2. Research papers and publications
3. Datasets and resources
4. Companies and organizations

Return the information in JSON format with sections and items."""
    
    def _create_merge_prompt(self, existing: str, new_items: List[Content]) -> str:
        new_content = "\n".join([
            f"- [{item.title}]({item.url}): {item.description}"
            for item in new_items
        ])
        
        return f"""Merge these new items into the existing content while maintaining organization and removing duplicates:

Existing Content:
{existing}

New Items:
{new_content}

Return the merged content in the same markdown format, preserving the section header.""" 