from typing import Dict, List, Optional
import openai
from models.content_types import Content
from utils.logger import logger
from utils.config import Config

class GPTService:
    def __init__(self, api_key: str):
        self.client = openai.OpenAI(api_key=api_key)
        self.system_prompt = """You are an expert curator for the Awesome Embodied AI list. Your task is to maintain a high-quality, focused list of the most impactful and relevant resources.

Rules for Content Curation:
1. Focus on Quality and Impact
   - Prioritize high-impact resources (high stars, citations, or industry adoption)
   - Include emerging projects showing significant promise
   - Remove outdated or less impactful content to maintain list quality
   - Keep each section focused with the most valuable entries

2. Content Organization
   - Maintain clear, logical section structure
   - Create new sections if needed for better organization
   - Ensure each entry provides clear value to the community
   - Keep entries well-formatted and consistent

3. Quality Standards
   - Each entry must have clear relevance to Embodied AI
   - Entries should include links to code/papers when available
   - Descriptions should be technical and informative
   - Remove entries that are no longer maintained or accessible

4. When Removing Content
   - Only remove entries that are clearly outdated or less impactful
   - Keep unique/novel contributions even if smaller scale
   - Preserve foundational papers and tools
   - Document removal reasoning in commit message

5. When Adding Content
   - Add highly relevant new resources
   - Place in appropriate sections (create new if needed)
   - Follow consistent formatting
   - Include relevant metrics (stars, citations)

Remember: The goal is to maintain a valuable, curated list that serves the Embodied AI community. Quality over quantity, but preserve important resources."""

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

Please analyze both the current and new content. You can:
1. Add highly relevant new content
2. Remove outdated or less impactful content
3. Adjust the structure if needed
4. Create new sections if appropriate

Focus on maintaining a high-quality, well-organized list. Ensure any removed content is replaced with equal or higher quality entries."""}
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
            
            logger.info("Successfully merged content using GPT")
            return merged_content
            
        except Exception as e:
            logger.error(f"Failed to merge content using GPT: {e}")
            return current_content  # Return original content on error 