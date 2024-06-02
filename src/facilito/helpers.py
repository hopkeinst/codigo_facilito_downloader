"""
Helpers
"""

import json
import os
import re
import subprocess
from typing import Any, Dict

from . import consts
from .models.video import Quality


def is_file(file: str, type_file: str) -> bool:
    """
    Checks if the file exists
    """
    return os.path.exists(file + "." + type_file)


def is_article_url(url: str) -> bool:
    """
    Checks if the provided url is a valid article url
    """
    pattern = re.compile(consts.ARTICLE_URL_REGEX)
    return bool(pattern.match(url))


def is_video_url(url: str) -> bool:
    """
    Checks if the provided url is a valid video url
    """
    pattern = re.compile(consts.VIDEO_URL_REGEX)
    return bool(pattern.match(url))


def is_course_url(url: str) -> bool:
    """
    Checks if the provided url is a valid course url
    """
    pattern = re.compile(consts.COURSE_URL_REGEX)
    return bool(pattern.match(url))


def is_bootcamp_url(url: str) -> bool:
    """
    Checks if the provided url is a valid bootcamp url
    """
    pattern = re.compile(consts.BOOTCAMP_URL_REGEX)
    return bool(pattern.match(url))


# TODO: implement error handling 👇
def to_netscape_string(cookie_data: list[dict]) -> str:
    """
    Convert cookies to Netscape cookie format.

    This function takes a list of cookie dictionaries and transforms them into
    a single string in Netscape cookie file format, which is commonly used by
    web browsers and other HTTP clients for cookie storage. The Netscape string
    can be used to programmatically interact with websites by simulating the
    presence of cookies that might be set during normal web browsing.

    Args:
        cookie_data (list of dict): A list of dictionaries where each dictionary
            represents a cookie. Each dictionary should have the following keys:
            - 'domain': The domain of the cookie.
            - 'expires': The expiration date of the cookie as a timestamp.
            - 'path': The path for which the cookie is valid.
            - 'secure': A boolean indicating if the cookie is secure.
            - 'name': The name of the cookie.
            - 'value': The value of the cookie.

    Returns:
        str: A string representing the cookie data in Netscape cookie file format.

    Example of Netscape cookie file format:
        .codigofacilito.com	TRUE	/	TRUE	0	CloudFront-Key-Pair-Id	APKAIAHLS7PK3GAUR2RQ
    """
    result = []
    for cookie in cookie_data:
        domain = cookie.get("domain", "")
        expiration_date = cookie.get("expires", 0)
        path = cookie.get("path", "")
        secure = cookie.get("secure", False)
        name = cookie.get("name", "")
        value = cookie.get("value", "")

        include_sub_domain = domain.startswith(".") if domain else False
        expiry = str(int(expiration_date)) if expiration_date > 0 else "0"

        result.append(
            [
                domain,
                str(include_sub_domain).upper(),
                path,
                str(secure).upper(),
                expiry,
                name,
                value,
            ]
        )

    return "\n".join("\t".join(cookie_parts) for cookie_parts in result)


def save_cookies_to_file(
    cookie_data: list[dict], file_path=consts.COOKIES_FILE
) -> None:
    """
    Save cookies to txt file
    """
    netscape_string = to_netscape_string(cookie_data)
    with open(file_path, "w", encoding="utf-8") as file:
        file.write("# Netscape HTTP Cookie File\n")
        file.write("# http://www.netscape.com/newsref/std/cookie_spec.html\n")
        file.write("# This is a generated file!  Do not edit.\n")
        file.write(netscape_string)


def quality_to_dlp_format(quality: Quality) -> str:
    """
    Convert quality enum to string
    """
    height = quality.value
    match quality:
        case Quality.BEST:
            dl_format = "bv+ba/b"
        case Quality.WORST:
            dl_format = "wv+wa/w"
        case Quality.P1080 | Quality.P720 | Quality.P480 | Quality.P360:
            dl_format = f"bv[height={height}]+ba/b[height={height}]"
        case _:
            dl_format = "bv+ba/b"

    return dl_format


def read_json(path: str) -> Dict[str, Any]:
    """
    Read json file.

    Args:
    path (str): The file path to the json file that will be read.

    Returns:
    Dict[str, Any]: A dictionary containing the parsed JSON data.
    """
    with open(path, "r", encoding="utf-8") as file:
        content = json.load(file)
        return content


def write_json(data: Dict[str, Any], path: str) -> None:
    """
    Write the JSON data to a file.

    Args:
        data (Dict[str, Any]): The data to write to the file.
        path (str): The path to the file where the JSON data will be written.
    """
    with open(path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4, ensure_ascii=False)


def clean_new_line(text: str) -> str:
    """
    Clean the string 'text' of new lines '\n'

    Args:
        text (str): String to clean

    Returns:
        str: Cleaned text string
    """
    return re.sub(consts.NEWLINE_NAME, " ", text).strip()


def clean_string(text: str) -> str:
    """
    This function cleans the input string by removing special
    characters and leading/trailing white spaces.

    Args:
        input_string (str): The input string to be cleaned.

    Returns:
        str: The cleaned string.
    """
    return re.sub(consts.SYMBOLS_NAME, "", text).strip()


def clean_title(title: str) -> str:
    """
    This function cleans the input string and updated the
    first character for title style

    Args:
        title (str): The input string to be cleaned and updated.

    Returns:
        str:  The cleaned string.
    """
    title = clean_new_line(title)
    title = clean_string(title)
    return title[0].upper() + title[1:]


def clean_video_sequence(a_tag) -> int:
    """
    Clean the number sequence of video

    Args:
        a_tag (ElementHandler): Element with HTML code

    Returns:
        int: Number sequence of video
    """
    p_tag = a_tag.query_selector("p[class*='no-margin h5 bold f-blues-text']")
    if p_tag is None:
        return 0
    p_tag = p_tag.inner_html()
    p_tag = clean_title(p_tag)
    match = re.search(consts.VIDEO_NUMBER, p_tag)
    if match is None:
        return 0
    return int(re.sub(consts.VIDEO_NUMBER, "", p_tag))


def clean_video_title(a_tag) -> str:
    """
    Clean the title of video

    Args:
        a_tag (ElementHandler): Element with HTML code

    Returns:
        str: Title of video
    """
    p_tag = a_tag.query_selector(
        "p[class*='ibm f-text-16 bold no-margin-bottom f-top-small']"
    )
    if p_tag is None:
        return ""
    p_tag = p_tag.inner_html()
    p_tag = clean_title(p_tag)
    return p_tag


def clean_class_sequence(a_tag) -> int:
    """
    Clean the number sequence of class

    Args:
        a_tag (ElementHandler): Element with HTML code

    Returns:
        int: Number sequence of class
    """
    p_tag = a_tag.query_selector("p[class*='no-margin h5 bold f-blues-text--2']")
    if p_tag is None:
        return 0
    p_tag = p_tag.inner_html()
    p_tag = clean_title(p_tag)
    match = re.search(consts.CLASS_NAME, p_tag)
    if match is None:
        return 0
    return int(match.group(1))


def clean_class_type(a_tag) -> str:
    """
    Clean the type of class

    Args:
        a_tag (ElementHandler): Element with HTML code

    Returns:
        str: Type of class
    """
    p_tag = a_tag.query_selector("p[class*='no-margin h5 bold f-blues-text--2']")
    if p_tag is None:
        return ""
    p_tag = p_tag.inner_html()
    p_tag = clean_title(p_tag)
    match = re.search(consts.CLASS_NAME, p_tag)
    if match is None:
        return ""
    return match.group(2)


def clean_play_url(url: str) -> str:
    """
    Clean the automatic play of URL into class

    Args:
        url (str): URL of class or course

    Returns:
        str: URL without play
    """
    if re.search(consts.PLAY_COURSE, url):
        url = re.sub(consts.PLAY_COURSE, "", url)
    return url


def clean_module_sequence(li_tag) -> int:
    """
    Clean the number sequence of module

    Args:
        li_tag (ElementHandler): Element with HTML code

    Returns:
        int: Number sequence of module
    """
    span_tag = li_tag.query_selector(
        "span[class='f-green-text f-green-text--2 bold h5']"
    )
    if span_tag is None:
        return 0
    span_tag = span_tag.inner_html()
    span_tag = clean_title(span_tag)
    return int(re.sub(consts.MODULE_NUMBER, "", span_tag))


def clean_module_title(li_tag) -> str:
    """
    Clean the title of module

    Args:
        li_tag (ElementHandler): Element with HTML code

    Returns:
        str: Title of module
    """
    h4_tag = li_tag.query_selector("h4")
    if h4_tag is None:
        return ""
    h4_tag = h4_tag.inner_html()
    h4_tag = clean_title(h4_tag)
    return h4_tag


def clean_bootcamp_title(bootcamp_title: str) -> str:
    """
    This function clean the input string by removing the initial
    string 'Bootcamp' or 'Bootcamp de'

    Args:
        bootcamp_title (str): The bootcamp title to be cleaned.

    Returns:
        str: The cleaned bootcamp title.
    """
    match = re.search(consts.BOOTCAMP_NAME, bootcamp_title)
    bootcamp_title = clean_new_line(bootcamp_title)
    if match:
        bootcamp_title = match.group(1)
        return clean_title(bootcamp_title)
    return clean_title(bootcamp_title)


def clean_course_title(course_title: str) -> str:
    """
    This function clean the input string by removing the initial
    string 'Curso' or 'Curso de'

    Args:
        course_title (str): The course title to be cleaned.

    Returns:
        str: The cleaned bootcamp title.
    """
    course_title = clean_new_line(course_title)
    pattern = re.compile(r"Curso(?:\s*de\s*)?(.*)", re.IGNORECASE)
    match = re.search(pattern, course_title)
    if match:
        course_title = match.group(1)
        return clean_title(course_title)
    return clean_title(course_title)


def check_dir(path: str) -> None:
    """
    Check if a given directory path exists and create it if it does not.

    Args:
        path (str): The path to check and create if necessary.

    Returns:
        None
    """
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)


def is_ffmpeg_installed() -> bool:
    """
    Check if ffmpeg is installed.

    Returns:
        bool: True if ffmpeg is installed, False otherwise.
    """
    try:
        subprocess.run(
            ["ffmpeg", "-version"],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return True
    except FileNotFoundError:
        return False
