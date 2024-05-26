"""
Article model
"""

from pydantic import BaseModel


class Article(BaseModel):
    """
    Article model
    """

    url: str
    title: str
    sequence: int = 0
    file_type: str = "pdf"
    size: int
    exists: bool = False
