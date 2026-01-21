"""
Cognitive Tools - Calculator, web search, Wikipedia, knowledge retrieval.

Tools that enhance agent reasoning capabilities:
- Mathematical calculations
- Web search
- Wikipedia lookup
- Knowledge retrieval
"""

from agent_tooling.tools.cognitive.calculator import calculate
from agent_tooling.tools.cognitive.search import web_search, wikipedia_search

__all__ = [
    "calculate",
    "web_search",
    "wikipedia_search",
]
