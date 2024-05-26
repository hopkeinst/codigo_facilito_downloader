"""
Codigo Facilito cli tool
"""

from typing import Annotated

import humanize
import typer
from rich import print as tprint
from rich.console import Console
from rich.table import Table

from facilito import consts, helpers
from facilito.core import Client
from facilito.errors import (
    BootcampError,
    ClassErrorName,
    CourseError,
    DownloadError,
    URLError,
    VideoError,
)
from facilito.models.video import Quality
from facilito.utils.logger import cli_logger

app = typer.Typer(
    rich_markup_mode="markdown",
    epilog="""
    Made with :heart: in [ivansaul](https://github.com/ivansaul)
    Modified by :neckbeard: :sunglasses: [hopkeinst](https://github.com/hopkeinst)
    """,
)


def download_article(url: str, path_dir: str = "", sequence: int = 0) -> bool:
    """
    Download an article

    Args:
        url (str): URL of the article to download
        sequence (int, optional): Number sequence in course. Defaults to 0.
    """
    with Client(headless=False, my_browser="chromium") as client:
        client.login()
        tprint(f"\n{consts.LOGIN_OK}\n")
        path = f"{consts.DOWNLOADS_DIR}"
        if path_dir != "":
            path += f"/{path_dir}"
        article = client.save_article(
            url=url, path=path, file_type=consts.FileType.PDF, sequence=sequence
        )
        if article is not None:
            size = humanize.naturalsize(article.size, format="%.2f")
            tprint(f"{consts.DOWNLOADING} [green]'[/green]", end="")
            if path_dir != "":
                tprint(f"[green]{path_dir} / [/green]")
            if sequence != 0:
                tprint(f"[green]{sequence:02d}. [/green]", end="")
            tprint(f"[green]{article.title}'[/green] ...")
            tprint(f"[default]\\[generic] Extracting URL: {article.url}[/default]")
            tprint(f"[default]\\[download] {path}/", end="")
            tprint(f"{article.title}.{article.file_type}[/default]", end="")
            tprint(" has already been downloaded")
            tprint(f"[default]\\[download] 100% of {size:>10s}[/default]")
            tprint(consts.VIDEO_DL_DONE)
            return True
        tprint("[bold red]Error![/bold red]", end=" ")
        tprint("Thats not a valid URL =>", end=" ")
        tprint(f"[green]{article.title}[/green]", end=" ")
        tprint(f"[link]{article.url}[/link]")
        return False


@app.command()
def download(
    url: Annotated[
        str,
        typer.Option(prompt=True),
    ],
    quality: Quality = typer.Option(
        prompt=True,
        default=Quality.BEST.value,
        prompt_required=True,
    ),
    headless: bool = False,
):
    """
    Downloads [ARTICLE|VIDEO|COURSE] from the provided URL.

    By default, it downloads the best quality video.
    """

    if not helpers.is_ffmpeg_installed():
        tprint(
            "[bold red]Error! [/bold red][bold magenta]ffmpeg is not installed.[/bold magenta]"
        )
        tprint(
            f"[bold magenta]Please [link={consts.FFMPEG_URL}]install[/link] it![/bold magenta]"
        )
        raise typer.Exit()

    if helpers.is_article_url(url):
        tprint(consts.PROCESSING)
        download_article(url=url)
        raise typer.Exit()

    if helpers.is_video_url(url):
        with Client(headless=headless) as client:
            tprint(consts.PROCESSING)
            client.login()
            tprint(f"\n{consts.LOGIN_OK}\n")
            try:
                video = client.video(url)
            except VideoError as e:
                tprint(consts.VIDEO_DL_ERROR_MAX)
                raise typer.Exit() from e
            max_retries = 5
            for attempt in range(1, max_retries + 1):
                try:
                    tprint(f"{consts.DOWNLOADING} '{video.title}' ...")
                    client.refresh_cookies()
                    video.download(quality=quality)
                except DownloadError:
                    if attempt < max_retries:
                        tprint(f"{consts.VIDEO_DL_ERROR_1} {consts.VIDEO_DL_ERROR_2}")
                    else:
                        tprint(consts.VIDEO_DL_ERROR_MAX)
                        break

                else:
                    tprint(consts.VIDEO_DL_DONE)
                    break
        raise typer.Exit()

    if helpers.is_course_url(url):
        with Client(headless=headless) as client:
            lst_errors_url = []
            tprint(consts.PROCESSING)
            client.login()
            tprint(f"\n{consts.LOGIN_OK}\n")
            try:
                course = client.course(url)
                course.title = helpers.clean_course_title(course.title)
                course_sections = course.sections
                # Course Details Table
                console = Console()
                sections_table = Table(
                    title=f"Curso - {course.title}",
                    title_style="bold",
                    title_justify="center",
                )
                sections_table.add_column("Sections", justify="left")
                sections_table.add_column("Videos", justify="right")
                for section in course_sections:
                    sections_table.add_row(
                        section.title,
                        str(len(section.videos_url)),
                    )
                console.print(sections_table)
            except CourseError as e:
                tprint("[red]✗[/red] Unable to download the course.")
                raise typer.Exit() from e

            # Confirm download
            confirm_download = typer.confirm("Would you like to download?")
            if not confirm_download:
                raise typer.Exit()

            # iterate over sections
            course_sections = course.sections
            for pfx_s, section in enumerate(course_sections, start=1):
                section.title = helpers.clean_title(section.title)
                for pfx_v, video_url in enumerate(section.videos_url, start=1):
                    if helpers.is_article_url(video_url.url):
                        if not download_article(
                            url=url,
                            path_dir=f"{pfx_s:02d}. {section.title}",
                            sequence=pfx_v,
                        ):
                            lst_errors_url.append(
                                {
                                    "section": section.title,
                                    "video_title": video_url.title,
                                    "url": video_url.url,
                                }
                            )
                    else:
                        try:
                            video = client.video(video_url.url)
                        except URLError as e:
                            tprint("[red]✗[/red] Unable to fetch the video from URL")
                            message = (
                                f"[SECTION] {section.title} [VIDEO] {video_url.url}"
                            )
                            cli_logger.error(message)
                            tprint("[bold red]Error![/bold red]", end=" ")
                            tprint("Thats not a valid video URL =>", end=" ")
                            tprint(f"[green]{video_url.title}[/green]", end=" ")
                            tprint(f"[link]{video_url.url}[/link]")
                            lst_errors_url.append(
                                {
                                    "section": section.title,
                                    "video_title": video_url.title,
                                    "url": video_url.url,
                                }
                            )
                            continue
                        except VideoError as e:
                            tprint("[red]✗[/red] Unable to fetch the video details")
                            message = (
                                f"[SECTION] {section.title} [VIDEO] {video_url.url}"
                            )
                            cli_logger.error(message)
                            continue
                        max_retries = 5
                        for attempt in range(1, max_retries + 1):
                            try:
                                tprint(f"{consts.DOWNLOADING}", end=" ")
                                tprint(
                                    f"[green]'{pfx_s:02d}. {section.title} / [/green]",
                                    end="",
                                )
                                tprint(
                                    f"[green]{pfx_v:02d}. {video.title}'[/green] ..."
                                )
                                client.refresh_cookies()
                                dir_path = f"{consts.DOWNLOADS_DIR}/"
                                dir_path += f"Curso - {course.title}/"
                                dir_path += f"{pfx_s:02d}. {section.title}"
                                video.download(
                                    quality=quality,
                                    dir_path=dir_path,
                                    prefix_name=f"{pfx_v:02d}. ",
                                )
                            except DownloadError:
                                if attempt < max_retries:
                                    tprint(
                                        f"{consts.VIDEO_DL_ERROR_1} {consts.VIDEO_DL_ERROR_2}"
                                    )
                                else:
                                    tprint(consts.VIDEO_DL_ERROR_MAX)
                                    break
                            else:
                                tprint(consts.VIDEO_DL_DONE)
                                break
            if len(lst_errors_url) > 0:
                tprint("[bold red]URLs with ERROR[/bold red]")
                for leu in lst_errors_url:
                    tprint("[yellow]-[/yellow]" * 70)
                    tprint(f"  [bold green]Section:[/bold green] {leu['section']}")
                    tprint("  [bold green]Title video|article:[/bold green]", end=" ")
                    tprint(f"{leu['video_title']}")
                    tprint(f"  [bold green]URL:[/bold green] [link]{leu['url']}[/link]")
                tprint("[yellow]-[/yellow]" * 70)
        raise typer.Exit()

    if helpers.is_bootcamp_url(url):
        with Client(headless=False) as client:
            tprint(consts.PROCESSING)
            client.login()
            tprint(f"\n{consts.LOGIN_OK}\n")
            try:
                tprint("[reverse white]   BOOTCAMP DETAILS   [/reverse white]\n")
                bootcamp = client.bootcamp(url)
                path_bootcamp = f"Bootcamp - {bootcamp.title}"
                print()
                console = Console()
                table_modules = Table(
                    title=f"{path_bootcamp} (resume)",
                    title_style="bold",
                    title_justify="center",
                )
                table_modules.add_column("Module", justify="left")
                table_modules.add_column("Classes", justify="right")
                table_modules.add_column("Videos", justify="right")
                for module in bootcamp.modules:
                    cnt_videos = 0
                    for class_ in module.classes:
                        cnt_videos += len(class_.videos)
                    table_modules.add_row(
                        module.title, str(len(module.classes)), str(cnt_videos)
                    )
                console.print(table_modules)
            except BootcampError as e:
                tprint(f"[bold red]✗[/bold red] Unable to download the bootcamp => {e}")
                cli_logger.error(e)
                raise typer.Exit()
            except ClassErrorName as e:
                tprint(
                    f"[red]✗[/red] Unable to fetch the name of class or course => {e}"
                )
                cli_logger.error(e)
            confirm_download = typer.confirm("Would you like to download?")
            if not confirm_download:
                raise typer.Exit()
            for module in bootcamp.modules:
                path_module = f"{module.sequence:02d}. {module.title}"
                for class_ in module.classes:
                    path_class = f"{class_.sequence:02d}. {class_.title}"
                    for video in class_.videos:
                        try:
                            video_down = client.video(video.url)
                            video_down.title = video.title
                        except VideoError as e:
                            tprint("[red]✗[/red] Unable to fetch the video details.")
                            message = f"[MODULE] {module.sequence:02d}. {module.title} "
                            message += f"[CLASS] {class_.sequence:02d} {class_.title} "
                            message += f"[VIDEO] {video.sequence:02d}. {video.title}"
                            cli_logger.error(message)
                            continue
                        max_retries = 5
                        for attempt in range(max_retries):
                            try:
                                tprint(f"{consts.DOWNLOADING}", end=" ")
                                tprint(f"[green]'{path_module} / [/green]", end="")
                                tprint(f"[green]{path_class} / [/green]", end="")
                                tprint(
                                    f"[green]{video.sequence:02d}. {video.title}'[/green] ..."
                                )
                                client.refresh_cookies()
                                dir_path = f"{consts.DOWNLOADS_DIR}/"
                                dir_path += f"{path_bootcamp}/"
                                dir_path += f"{path_module}/"
                                dir_path += f"{path_class}"
                                video_down.download(
                                    quality=quality,
                                    dir_path=dir_path,
                                    prefix_name=f"{video.sequence:02d}. ",
                                )
                            except DownloadError:
                                if attempt < max_retries:
                                    tprint(
                                        f"{consts.VIDEO_DL_ERROR_1} {consts.VIDEO_DL_ERROR_2}"
                                    )
                                else:
                                    tprint(consts.VIDEO_DL_ERROR_MAX)
                                    break
                            else:
                                tprint(consts.VIDEO_DL_DONE)
                                break
        raise typer.Exit()


@app.command()
def login():
    """
    Authenticates a user with the given email and password.
    """
    while True:
        email = typer.prompt("What's your email?")
        confirm_email = typer.prompt("Confirm your email?")
        if email == confirm_email:
            break

        tprint(
            "[bold red]Error![/bold red] [magenta]The two entered values do not match.[/magenta]"
        )

    while True:
        password = typer.prompt("What's your password?", hide_input=False)
        confirm_password = typer.prompt("Confirm your password?", hide_input=False)
        if password == confirm_password:
            break

        tprint(
            "[bold red]Error![/bold red] [magenta]The two entered values do not match.[/magenta]"
        )

    # save credentials
    user = {"email": email, "password": password}
    helpers.write_json(data=user, path=consts.CONFIG_FILE)


if __name__ == "__main__":
    app()
