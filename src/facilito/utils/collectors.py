"""Collectors for Facilito API"""

import os
import re
from typing import Optional

from playwright.sync_api import Page
from rich import print as tprint

from .. import consts
from ..errors import BootcampError, CourseError, URLError, VideoError
from ..helpers import (
    clean_bootcamp_title,
    clean_class_sequence,
    clean_class_type,
    clean_module_sequence,
    clean_module_title,
    clean_play_url,
    clean_title,
    clean_video_sequence,
    clean_video_title,
    is_bootcamp_url,
    is_course_url,
    is_video_url,
)
from ..models.bootcamp import Bootcamp, BootcampClass, BootcampModule, BootcampVideo
from ..models.course import Course, CourseSection, VideoURL
from ..models.video import MediaType, Video
from ..utils import expanders
from ..utils.logger import logger


def get_article_sync(url: str, page: Page) -> Page:
    """
    Get info by article
    """
    page.goto(url=url, wait_until=None)
    page.evaluate(
        """
        let elements_to_delete = document.querySelectorAll("div[class='player-header']");
        for (let element of elements_to_delete) {
            element.parentNode.removeChild(element);
        }
    """
    )
    page.evaluate(
        """
        elements_to_delete = document.querySelectorAll("div[class='row f-gap-medium middle-xs']");
        for (let element of elements_to_delete) {
            element.parentNode.removeChild(element);
        }
    """
    )
    page.evaluate(
        """
        elements_to_delete = document.querySelectorAll("div[class='player-sidebar relative']");
        for (let element of elements_to_delete) {
            element.parentNode.removeChild(element);
        }
    """
    )
    return page


def get_video_detail_sync(url: str, page: Page) -> Video:
    """Retrieve detailed information for a video from its URL.

    Args:
        url (str): The URL of the video page.
        page (Page): The Playwright page object.

    Returns:
        Video: An instance of the Video model with the retrieved details.
    """

    if not is_video_url(url):
        error_message = f"[VIDEO] Invalid video URL: {url}"
        logger.error(error_message)
        raise URLError(error_message)

    page.goto(url=url, wait_until=None)

    # search video title
    try:
        title = page.locator(
            """
            h1[class='ibm bold-600 no-margin f-text-22'],
            h1[class='ibm bold-600 no-margin f-text-48']
            """
        ).inner_text()
        title = clean_title(title)
    except Exception as e:
        error_message = f"[VIDEO] title not found: {url}"
        logger.error(error_message)
        raise VideoError(error_message) from e

    video_id = page.locator("input[name='video_id']").first.get_attribute("value")
    course_id = page.locator("input[name='course_id']").first.get_attribute("value")

    if video_id is None or course_id is None:
        error_message = f"[VIDEO] id not found: {url}"
        logger.error(error_message)
        raise VideoError(error_message)

    # get video m3u8 url
    base_m3u8_url = "https://video-storage.codigofacilito.com"
    m3u8_url = f"{base_m3u8_url}/hls/{course_id}/{video_id}/playlist.m3u8"

    # check media type
    media_type: Optional[MediaType] = None

    if "/videos/" in url:
        media_type = MediaType.STREAMING
    if "/articulos/" in url:
        media_type = MediaType.READING

    return Video(
        id=video_id,
        url=url,
        m3u8_url=m3u8_url,
        title=title,
        media_type=media_type,
        description=None,
    )


# TODO: improve this function, handles more error cases 👇
def get_course_detail_sync(url: str, page: Page) -> Course:
    """
    Retrieves detailed information about a course from a given URL.

    Args:
        url (str): The URL of the course to be detailed.
        page (Page): The playwright page object to interact with the webpage.

    Returns:
        Course: An object containing the course details.
    """
    url = clean_play_url(url)
    if not is_course_url(url):
        error_message = f"[COURSE] Invalid course URL: {url}"
        logger.error(error_message)
        raise URLError(error_message)

    page.goto(url=url, wait_until=None)

    # expand collapsed sections
    expanders.expand_course_sections(page)

    # get course title
    title = page.title()

    # get course sections
    try:
        sections = _get_sections(page)
    except Exception as e:
        error_message = f"[COURSE] an error occurred: {url}"
        logger.error(error_message)
        raise CourseError(error_message) from e

    course = Course(
        url=url,
        title=title,
        sections=sections,
    )

    return course


def get_bootcamp_detail_sync(url: str, page: Page) -> Bootcamp:
    """
    Retrieves detailed information about a bootcamp from a given URL.

    Args:
        url (str): The URL of the bootcamp to be detailed.
        page (Page): The playwright page object to interact with the webpage.

    Returns:
        Bootcamp: An object containing the bootcamp details."""

    if not is_bootcamp_url(url):
        error_message = f"[BOOTCAMP] Invalid course URL: {url}"
        logger.error(error_message)
        raise URLError(error_message)

    page.goto(url=url, wait_until=None)
    expanders.expand_bootcamps_modules(page)

    # get bootcamp title
    bootcamp_title = clean_bootcamp_title(page.title())

    tprint(
        f"[bold red]Bootcamp title:[/bold red] [bright_red]{bootcamp_title}[/bright_red]"
    )

    dict_info = {
        "bootcamp_name": f"Bootcamp - {bootcamp_title}",
    }

    # get bootcamp modules
    try:
        all_modules = _get_modules(page=page, dict_info=dict_info)
        bootcamp_obj = Bootcamp(url=url, title=bootcamp_title, modules=all_modules)
        return bootcamp_obj
    except Exception as e:
        error_message = f"[BOOTCAMP] an error occurred: {url}"
        logger.error(error_message)
        raise BootcampError(error_message) from e


def _get_sections(page: Page) -> list[CourseSection]:
    """Get course sections from a page.

    This function collects all course sections from the given page by looking for
    specific HTML div elements with class 'f-top-16' and extracts their corresponding titles.

    Args:
        page (Page): The playwright page object representing the web page.

    Returns:
        list[CourseSection]: A list of CourseSection objects.
    """
    sections: list[CourseSection] = []

    # possibly some containers are empty
    sections_container_divs = page.query_selector_all("div[class='f-top-16']")

    for div in sections_container_divs:
        title_match = div.query_selector("h4")
        if title_match is None:
            continue

        logger.debug("[Section Title] %s", title_match.inner_text())

        a_tags = div.query_selector_all("a")
        all_videos: list[VideoURL] = []
        for a_tag in a_tags:
            p_element_title = a_tag.query_selector(
                "p[class='ibm f-text-16 bold no-margin-bottom f-top-small']"
            )
            if p_element_title is not None:
                video_title = p_element_title.inner_text()
                video_url = a_tag.get_attribute("href")
                video_url_obj = VideoURL(
                    title=video_title,
                    url=f"{consts.BASE_URL}{video_url}",
                )
                all_videos.append(video_url_obj)

        logger.debug("This section has %s videos", len(all_videos))

        sections.append(
            CourseSection(
                title=title_match.inner_text(),
                videos_url=all_videos,
            ),
        )

    return sections


def _get_videos(url: str, page: Page, dict_info: dict) -> list[BootcampVideo]:
    """Get course sections from a page.

    Args:
        url (str): URL of video
        page (Page):  The Playwright page object.
        dict_info (dict): Dict with info about the module and class parents

    Returns:
        list[BootcampVideo]: List with video objects of the class
    """
    try:
        page.goto(url=url, wait_until=None)
        div_collapsible = page.query_selector(
            "div[class*='collapsible-body no-border topics-li']"
        )
        if div_collapsible is None:
            return []
        a_tags = div_collapsible.query_selector_all("a")
        if a_tags == []:
            return []
        videos_class: list[BootcampVideo] = []
        for a_tag in a_tags:
            video_url = a_tag.get_attribute("href")
            video_sequence = clean_video_sequence(a_tag)
            video_title = clean_video_title(a_tag)
            if not re.fullmatch(consts.CLASS_BOOTCAMP_NAME, video_title):
                pattern = re.compile(consts.CLASS_BOOTCAMP_NAME, re.IGNORECASE)
                match = re.search(pattern, video_title)
                if match:
                    video_title = match.group(1)
            video_title = clean_title(video_title)
            tprint("      [bold green]Video title:[/bold green]", end=" ")
            tprint(f"[green]{video_sequence:02d}. {video_title}[/green]")
            video_obj = BootcampVideo(
                url=f"{consts.BASE_URL}{video_url}",
                sequence=video_sequence,
                title=video_title,
            )
            videos_class.append(video_obj)
        return videos_class
    except Exception as e:
        error_message = (
            f"[MODULE] {dict_info['module_sequence']:02d}. {dict_info['module_title']} "
        )
        error_message += (
            f"[CLASS] {dict_info['class_sequence']:02d}. {dict_info['class_title']} "
        )
        error_message += f"=> {e}"
        logger.error(error_message)
        tprint(f"Exception: {e}")
        return []


def _get_classes(a_tags, page: Page, dict_info: dict) -> list[BootcampClass]:
    """
    Get information about the classes that make up
    a bootcamp module

    Args:
        a_tags (_type_): All hyperlinks into page / website
        path (str): Father dir path
        page (Page): Page
        dict_info (dict): Dictionary with information to use

    Raises:
        ClassErrorName: When a class has no name

    Returns:
        list[BootcampClass]: List with all information of classes
    """

    all_classes: list[BootcampClass] = []
    for a_tag in a_tags:
        p_title = a_tag.query_selector(
            "p[class='ibm f-text-16 bold no-margin-bottom f-top-small']"
        )
        class_type = clean_class_type(a_tag)
        class_sequence = clean_class_sequence(a_tag)
        if p_title is not None:
            class_title = clean_title(p_title.inner_html())
            class_url = consts.BASE_URL + a_tag.get_attribute("href")
            if class_type != "Curso":
                tprint("    [bold magenta]Class Title:[/bold magenta]", end=" ")
                tprint(
                    f"[bright_magenta]{class_sequence:02d}. {class_title}[/bright_magenta]"
                )
                new_page = page.context.new_page()
                all_videos = _get_videos(
                    class_url,
                    new_page,
                    dict_info={
                        "bootcamp_name": dict_info["bootcamp_name"],
                        "module_sequence": dict_info["module_sequence"],
                        "module_title": dict_info["module_title"],
                        "class_sequence": class_sequence,
                        "class_title": class_title,
                    },
                )
                while not new_page.is_closed():
                    new_page.close()
                all_classes.append(
                    BootcampClass(
                        sequence=class_sequence,
                        title=class_title,
                        url=f"{consts.BASE_URL}{class_url}",
                        videos=all_videos,
                    )
                )
            else:
                _print_error_class(
                    dict_info={
                        "bootcamp_name": dict_info["bootcamp_name"],
                        "module_sequence": dict_info["module_sequence"],
                        "module_title": dict_info["module_title"],
                        "class_sequence": class_sequence,
                        "class_title": class_title,
                        "class_url": class_url,
                    },
                )
        else:
            error_message = (
                f"[MODULE] {dict_info['module_title']} [CLASS] {class_sequence:02d}"
            )
            logger.error(error_message)
    return all_classes


def _get_modules(page: Page, dict_info: dict) -> list[BootcampModule]:
    """
    Get bootcamp modules from a page.

    Args:
        page (Page): The playwright page object representing the web page.

    Returns:
        list[BootcampModule]: A list of BootcampModule objects.
    """

    all_modules: list[BootcampModule] = []
    li_tags = page.query_selector_all("li[class*='f-radius-small']")
    for li_tag in li_tags:
        module_title = clean_module_title(li_tag)
        module_sequence = clean_module_sequence(li_tag)
        if li_tag.query_selector("span[class='bold f-yellow-text']") is not None:
            logger.debug("[Module Title] %s", module_title)
            logger.debug("WARNING: Module not charged yet")
            tprint("  [bold cyan]Module Title:[/bold cyan]", end=" ")
            tprint(f"[bright_cyan]{module_sequence:02d}. {module_title}[/bright_cyan]")
            tprint("    [yellow]\\[WARNING] Module not charged yet[/yellow]")
            all_modules.append(
                BootcampModule(
                    sequence=module_sequence,
                    title=module_title,
                    classes=[],
                )
            )
            continue
        if module_title is None:
            continue
        logger.debug("[Module Title] %s", module_title)
        tprint("  [bold cyan]Module Title:[/bold cyan]", end=" ")
        tprint(f"[bright_cyan]{module_sequence:02d}. {module_title}[/bright_cyan]")
        a_tags = li_tag.query_selector_all("a")
        all_classes = _get_classes(
            a_tags=a_tags,
            page=page,
            dict_info={
                "bootcamp_name": dict_info["bootcamp_name"],
                "module_sequence": module_sequence,
                "module_title": module_title,
            },
        )
        all_modules.append(
            BootcampModule(
                sequence=module_sequence, title=module_title, classes=all_classes
            )
        )

    return all_modules


def _generate_file_course(path: str, file_name: str, type_file: str, url: str) -> bool:
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)
    with open(f"{path}{file_name}.{type_file}", "w", encoding="utf-8") as f:
        f.write("  -- CURSO NO CLASE --  \n")
        f.write("En este bootcamp, esta no es una clase sino un curso completo,")
        f.write(" puede revisarlo:\n")
        f.write(f"Curso: {file_name} => {url}\n")
        f.write("  -- CURSO NO CLASE --  \n")
    return os.path.exists(f"{path}{file_name}.{type_file}")


def _print_error_class(dict_info: dict):
    tprint("[blink bold red]  -- CURSO NO CLASE --  [/blink bold red]")
    tprint("La siguiente no es una clase sino un curso completo, revisarlo:")
    tprint("[bold bright_blue][MODULO][/bold bright_blue]", end=" ")
    tprint(f"[bright_blue]{dict_info['module_sequence']:02d}. [/bright_blue]", end="")
    tprint(f"[bright_blue]{dict_info['module_title']}[/bright_blue]")
    tprint("[bold yellow][CURSO][/bold yellow]", end=" ")
    tprint(f"[yellow]{dict_info['class_sequence']:02d}. [/yellow]", end="")
    tprint(f"[yellow]{dict_info['class_title']}[/yellow]", end=" ")
    tprint(f"=> [link]{dict_info['class_url']}[/link]")
    tprint("[blink bold red]  -- CURSO NO CLASE --  [/blink bold red]")
    path = f"{consts.DOWNLOADS_DIR}/"
    path += f"{dict_info['bootcamp_name']}/"
    path += f"{dict_info['module_sequence']:02d}. {dict_info['module_title']}/"
    if not _generate_file_course(
        path=path,
        file_name=f"{dict_info['class_sequence']:02d}. {dict_info['class_title']}",
        type_file="txt",
        url=dict_info["class_url"],
    ):
        tprint("[bold red]Error ![/bold red] generating file => ", end="")
        tprint(f"{dict_info['class_sequence']:02d}. {dict_info['class_title']}")


__all__ = [
    "get_video_detail_sync",
    "get_course_detail_sync",
    "get_bootcamp_detail_sync",
]
