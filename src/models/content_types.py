from dataclasses import dataclass
from typing import Optional, List

@dataclass
class Content:
    title: str
    url: str
    description: Optional[str] = None
    
@dataclass
class Section:
    name: str
    items: List[Content] 