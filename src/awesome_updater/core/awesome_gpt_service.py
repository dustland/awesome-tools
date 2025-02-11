from typing import Optional, Dict, List
from utils.gpt_service import GPTService
from utils.logger import logger

class AwesomeGPTService:
    """Specialized GPT service for Awesome List operations."""
    
    # System prompts
    CURATOR_PROMPT = """You are an expert curator for the Awesome Embodied AI list. Your task is to maintain a high-quality, focused list of the most impactful and relevant resources.

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
   - Maintain table alignment and formatting"""
    
    TITLE_PROMPT = """You are a technical writer specializing in making research content engaging while maintaining accuracy.
Your task is to rewrite titles to be more engaging while preserving technical accuracy and key terms."""
    
    def __init__(self, gpt_service: GPTService):
        """Initialize with a GPT service instance."""
        self.gpt = gpt_service
        
    def generate_attractive_title(self, title: str) -> str:
        """Generate a more engaging version of an article title."""
        prompt = f"""Make this article title more engaging and attention-grabbing while maintaining accuracy and professionalism. 
        Keep the same key information but make it more compelling:
        
        Original: {title}
        
        Requirements:
        - Keep it concise (max 100 characters)
        - Maintain technical accuracy
        - Make it engaging but professional
        - Keep key terms like 'Embodied AI', 'Robotics', etc.
        - Don't use clickbait tactics
        """
        
        try:
            new_title = self.gpt.complete(
                prompt=prompt,
                system_prompt=self.TITLE_PROMPT,
                max_tokens=100,
                temperature=0.7
            )
            return new_title if new_title else title
        except Exception as e:
            logger.error(f"Failed to generate attractive title: {e}")
            return title
            
    def merge_content(self, current_content: str, new_content: str) -> str:
        """Merge new content into existing awesome list content."""
        try:
            if not current_content.strip():
                logger.warning("Current content is empty, cannot merge")
                return current_content

            prompt = f"""Here is the current content:
{current_content}

Here is the new content to analyze and potentially merge:
{new_content}

Please analyze both the current and new content. Your task is to:
1. Add relevant new content to appropriate sections
2. Maintain exact table and list formatting
3. Keep entries organized alphabetically within sections
4. Remove less impactful content if needed
5. Preserve the structure and hierarchy

Focus on maintaining a high-quality, well-organized list while preserving the exact formatting."""

            merged_content = self.gpt.complete(
                prompt=prompt,
                system_prompt=self.CURATOR_PROMPT,
                max_tokens=4000,
                temperature=0.1  # Low temperature for consistent curation
            )
            
            if not merged_content:
                return current_content
                
            # Safety checks
            if len(merged_content) < len(current_content) * 0.5:
                logger.warning("Merged content is too short, might have lost valuable content")
                return current_content
            
            content_indicators = ["github.com", "arxiv.org", "doi.org"]
            current_indicators = sum(1 for i in content_indicators if i in current_content)
            merged_indicators = sum(1 for i in content_indicators if i in merged_content)
            
            if merged_indicators < current_indicators * 0.7:
                logger.warning("Merged content has lost too many valuable references")
                return current_content
            
            if "| ----------" not in merged_content and "| ----------" in current_content:
                logger.warning("Merged content has lost table formatting")
                return current_content
            
            logger.info("Successfully merged content using GPT")
            return merged_content
            
        except Exception as e:
            logger.error(f"Failed to merge content using GPT: {e}")
            return current_content 