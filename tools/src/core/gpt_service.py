from typing import Dict, List, Optional
import openai
from models.content_types import Content
from utils.logger import logger
from utils.config import Config

class GPTService:
    def __init__(self, api_key: str):
        self.client = openai.OpenAI(api_key=api_key)
        self.system_prompt = """You are an expert curator for the Awesome Embodied AI list. Your task is to maintain a high-quality, focused list of the most impactful and relevant resources.

Rules for Content Structure:
1. Maintain Existing Format
   - Keep the exact table structure for papers: | Name | Description | Paper | Code |
   - Keep the list format for tools and products: - [Name](link) - Description [⭐Stars]
   - Preserve all existing sections and their hierarchy
   - Keep the table headers and alignment exactly as they are

2. Content Organization
   - Place papers in appropriate paper sections (Survey, LLM-Driven, Robotics, etc.)
   - Place tools in the Open Source Projects section
   - Place products in the Companies & Products section
   - Create new subsections only if truly needed

3. Quality Standards
   - Each entry must be directly related to Embodied AI
   - Papers must have either arxiv/doi links or GitHub implementations
   - Tools must have active GitHub repositories
   - Descriptions should be technical and concise

4. When Merging Content
   - Add new high-impact content in the appropriate sections
   - Keep entries organized alphabetically within sections
   - Remove outdated or less relevant content
   - Preserve foundational papers and tools
   - Maintain table alignment and formatting

5. Content Format Examples:
   Paper entry:
   | GPT4V | MLM(Image+Language->Language) | [Paper](https://arxiv.org/abs/2303.08774) | |

   Tool entry:
   - [Isaac Sim](https://developer.nvidia.com/isaac-sim) - NVIDIA's robotics simulator with photorealistic rendering [⭐5000]

Remember: The goal is to maintain a valuable, well-organized list that serves the Embodied AI community. Preserve the exact formatting while ensuring high-quality content."""

    def merge_content(self, current_content: str, new_content: str) -> str:
        """Merge new content into existing content using GPT."""
        try:
            if not current_content.strip():
                logger.warning("Current content is empty, cannot merge")
                return current_content

            messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": f"""Here is the current content:
{current_content}

Here is the new content to analyze and potentially merge:
{new_content}

Please analyze both the current and new content. Your task is to:
1. Add relevant new content to appropriate sections
2. Maintain exact table and list formatting
3. Keep entries organized alphabetically within sections
4. Remove less impactful content if needed
5. Preserve the structure and hierarchy

Focus on maintaining a high-quality, well-organized list while preserving the exact formatting."""}
            ]
            
            response = self.client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=messages,
                temperature=0.1,  # Low temperature for consistent curation
                max_tokens=4000
            )
            
            merged_content = response.choices[0].message.content
            
            # Safety check: ensure minimum content preservation
            if len(merged_content) < len(current_content) * 0.5:
                logger.warning("Merged content is too short, might have lost valuable content")
                return current_content
            
            # Safety check: ensure key content types are preserved
            content_indicators = [
                "github.com",  # GitHub repositories
                "arxiv.org",   # Research papers
                "doi.org"      # Academic references
            ]
            
            current_indicators = sum(1 for indicator in content_indicators if indicator in current_content)
            merged_indicators = sum(1 for indicator in content_indicators if indicator in merged_content)
            
            if merged_indicators < current_indicators * 0.7:  # Allow some reduction but not too much
                logger.warning("Merged content has lost too many valuable references")
                return current_content
            
            # Safety check: ensure table structure is preserved
            if "| ----------" not in merged_content and "| ----------" in current_content:
                logger.warning("Merged content has lost table formatting")
                return current_content
            
            logger.info("Successfully merged content using GPT")
            return merged_content
            
        except Exception as e:
            logger.error(f"Failed to merge content using GPT: {e}")
            return current_content  # Return original content on error 