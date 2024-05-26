"""
Article model
"""

from typing import Optional

from pydantic import BaseModel

from ..utils.logger import logger


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
