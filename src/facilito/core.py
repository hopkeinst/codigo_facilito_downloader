"""
Synchronous Client to scrape data from Codigo Facilito.
"""

import json
import os
from typing import Optional

from playwright.sync_api import sync_playwright

from . import consts, helpers
from .consts import FileType
from .errors import ClientError
from .models.account import Account
from .models.article import Article
from .models.bootcamp import Bootcamp
from .models.course import Course
from .models.video import Video
from .utils import collectors


class Client:
    """
    Represents a client capable of handling requests
    with Codigo Facilito.
    """

    def __init__(
        self,
        account: Optional[Account] = None,
        headless: bool = False,
        navigation_timeout: int = 30 * 1000,
        navigation_retries: int = 5,
        my_browser: str = "firefox"
    ):
        self.account = account
        self.headless = headless
        self.navigation_timeout = navigation_timeout
        self.navigation_retries = navigation_retries
        self.my_browser = my_browser

    def __enter__(self):
        # pylint: disable=attribute-defined-outside-init
        self._playwright = sync_playwright().start()
        if self.my_browser == "chromium":
            self._browser = self._playwright.chromium.launch(headless=self.headless)
        else:
            self._browser = self._playwright.firefox.launch(headless=self.headless)
        self._context = self._browser.new_context()
        self._context.set_default_navigation_timeout(self.navigation_timeout)
        self._page = self._context.new_page()

        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self._context.close()
        self._browser.close()
        self._playwright.stop()

    @property
    def playwright(self):
        """
        The playwright instance used for data scraping.
        """
        if not hasattr(self, "_playwright"):
            raise ClientError(consts.CLIENT_ERROR)
        return self._playwright

    @property
    def browser(self):
        """
        The browser instance used for data scraping.
        """
        if not hasattr(self, "_browser"):
            raise ClientError(consts.CLIENT_ERROR)
        return self._browser

    @property
    def context(self):
        """
        The context instance used for data scraping.
        """
        if not hasattr(self, "_context"):
            raise ClientError(consts.CLIENT_ERROR)
        return self._context

    @property
    def page(self):
        """
        The page instance used for data scraping.
        """
        if not hasattr(self, "_page"):
            raise ClientError(consts.CLIENT_ERROR)
        return self._page

    def video(self, url: str) -> Video:
        """
        Fetch a Codigo Facilito video by its URL.

        Args:
            url (str): The URL of the video to fetch.
        Returns:
            Video: An instance of Video class containing the details of the fetched video.
        Raises:
            URLError: If the URL provided is invalid.
        """
        page = self.page
        video = collectors.get_video_detail_sync(url, page)
        return video

    def course(self, url: str) -> Course:
        """
        Get course
        """
        page = self.page
        course = collectors.get_course_detail_sync(url, page)
        return course

    def bootcamp(self, url: str) -> Bootcamp:
        """
        Get bootcamp
        """
        page = self.page
        bootcamp = collectors.get_bootcamp_detail_sync(url, page)
        return bootcamp

    def take_screenshot(self, url: str, path: str = "screenshot.png"):
        """
        Take screenshot page
        """
        page = self.page
        page.goto(url)
        page.screenshot(path=path)

    def save_article(
        self, url: str, path: str, file_type: FileType, sequence: int = 0
    ) -> Optional[Article]:
        """
        Save page as pdf or html
        """
        article = None
        page = self.page
        page = collectors.get_article_sync(url=url, page=page)
        title = page.title()
        title = helpers.clean_new_line(title)
        title = helpers.clean_string(title)
        if sequence != 0:
            title = f"{sequence:02d}. {title}"
        if os.path.exists(f"{path}/{title}.{file_type.value}"):
            size = os.path.getsize(f"{path}/{title}.{file_type.value}")
            article = Article(
                    url=url,
                    title=title,
                    file_type=file_type.value,
                    size=size,
                    exists=True
                )
        else:
            page.emulate_media(media="screen")
            page.pdf(path=f"{path}/{title}.{file_type.value}", print_background=True)
            if os.path.exists(f"{path}/{title}.{file_type.value}"):
                size = os.path.getsize(f"{path}/{title}.{file_type.value}")
                article = Article(
                    url=url,
                    title=title,
                    file_type=file_type.value,
                    size=size
                )
        return article


    def login(self):
        """
        Login
        """
        with open(consts.CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        email = data["email"]
        pswd = data["password"]
        page = self.page
        page.goto(url=consts.LOGIN_URL)
        email_input = page.locator("#sign_in_email_field")
        email_input.fill(email)
        pswd_input = page.locator("#sign_in_password_field")
        pswd_input.fill(pswd)
        btn_submit = page.locator("button[type='submit']")
        btn_submit.click()
        page.wait_for_url(consts.POST_LOGIN_URL)
        cookies = page.context.cookies(consts.BASE_URL)
        helpers.save_cookies_to_file(cookies, consts.COOKIES_FILE)

    def refresh_cookies(self) -> None:
        """
        Refresh cookies from current context
        """
        page = self.page
        cookies = page.context.cookies(consts.BASE_URL)
        helpers.save_cookies_to_file(cookies, consts.COOKIES_FILE)
