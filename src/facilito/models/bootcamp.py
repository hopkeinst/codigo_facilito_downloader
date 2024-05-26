""" Bootcamp model """

from pydantic import BaseModel


class BootcampVideo(BaseModel):
    """Video model, video of URL"""
    sequence: int
    title: str
    url: str


class BootcampClass(BaseModel):
    """BootcampClass model"""
    sequence: int
    title: str
    url: str
    videos: list[BootcampVideo]


class BootcampModule(BaseModel):
    """BootcampModule model"""
    sequence: int
    title: str
    classes: list[BootcampClass]


class Bootcamp(BaseModel):
    """Bootcamp model"""
    url: str
    title: str
    modules: list[BootcampModule]
