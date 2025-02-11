from typing import Optional, Dict, Any, List
from openai import OpenAI
from utils.logger import logger

class GPTService:
    """A general-purpose GPT service for text generation and completion tasks."""
    
    def __init__(self, api_key: str, model: str = "gpt-4o"):
        """Initialize the GPT service.
        
        Args:
            api_key: OpenAI API key
            model: GPT model to use (default: gpt-4o)
        """
        logger.debug(f"Initializing GPT service with key starting with: {api_key[:8] if api_key else 'None'}")
        if not api_key:
            raise ValueError("OpenAI API key is required")
            
        if api_key == 'your_openai_key' or api_key == 'your_api_key':
            raise ValueError("Invalid OpenAI API key: using placeholder value")
            
        self.api_key = api_key
        self.model = model
        self.client = OpenAI(api_key=api_key)
        logger.debug(f"GPT service initialized with model: {model}")
        
    def complete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        messages: Optional[List[Dict[str, str]]] = None,
        **kwargs: Any
    ) -> Optional[str]:
        """Generate completion using GPT model.
        
        Args:
            prompt: The user prompt to generate from
            system_prompt: Optional system prompt to set context
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature (0-1)
            messages: Optional list of message dicts for chat history
            **kwargs: Additional parameters to pass to OpenAI API
            
        Returns:
            Generated text or None if generation fails
        """
        try:
            # Build messages list
            if messages is None:
                messages = []
                if system_prompt:
                    messages.append({"role": "system", "content": system_prompt})
                messages.append({"role": "user", "content": prompt})
            
            # Call OpenAI API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                **kwargs
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"Error in GPT completion: {e}")
            return None
            
    def stream_complete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        messages: Optional[List[Dict[str, str]]] = None,
        **kwargs: Any
    ) -> Optional[str]:
        """Stream completion using GPT model.
        
        Same parameters as complete(), but streams the response.
        """
        try:
            # Build messages list
            if messages is None:
                messages = []
                if system_prompt:
                    messages.append({"role": "system", "content": system_prompt})
                messages.append({"role": "user", "content": prompt})
            
            # Call OpenAI API with streaming
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                stream=True,
                **kwargs
            )
            
            # Stream the response
            collected_chunks = []
            for chunk in response:
                if chunk.choices[0].delta.content is not None:
                    collected_chunks.append(chunk.choices[0].delta.content)
                    # Could yield here if needed: yield chunk.choices[0].delta.content
            
            return "".join(collected_chunks).strip()
            
        except Exception as e:
            logger.error(f"Error in GPT streaming: {e}")
            return None

    def generate_text(self, prompt: str, system_prompt: str = None, max_tokens: int = 150, temperature: float = 0.7) -> Optional[str]:
        """Generate text using GPT model."""
        try:
            messages = [
                {"role": "system", "content": system_prompt or "You are a helpful assistant that generates engaging and accurate content."},
                {"role": "user", "content": prompt}
            ]
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Error generating text with GPT: {e}")
            return None
            
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
            new_title = self.generate_text(prompt, max_tokens=100, temperature=0.7)
            return new_title if new_title else title
        except Exception as e:
            logger.error(f"Failed to generate attractive title: {e}")
            return title  # Fallback to original title
            
    def merge_awesome_list_content(self, current_content: str, new_content: str) -> str:
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

            merged_content = self.generate_text(
                prompt=prompt,
                system_prompt="You are an expert curator for the Awesome Embodied AI list. Your task is to maintain a high-quality, focused list of the most impactful and relevant resources.",
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
            return current_content  # Return original content on error 