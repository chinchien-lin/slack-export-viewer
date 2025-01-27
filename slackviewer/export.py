import os.path
import shutil
from datetime import datetime

from slackviewer.reader import Reader
from slackviewer.archive import get_export_info
from jinja2 import Environment, PackageLoader

import pkgutil

def export(archive_dir):
    """
    Generates a single-file printable export for an archive file or directory
    """
    css = pkgutil.get_data('slackviewer', 'static/viewer.css').decode('utf-8')
    tmpl = Environment(loader=PackageLoader('slackviewer')).get_template("export_single.html")
    export_file_info = get_export_info(archive_dir)
    r = Reader(export_file_info["readable_path"])
    channel_list = sorted(
        [{"channel_name": k, "messages": v} for (k, v) in r.compile_channels().items()],
        key=lambda d: d["channel_name"]
    )

    html = tmpl.render(
        css=css,
        generated_on=datetime.now(),
        workspace_name=export_file_info["workspace_name"],
        source_file=export_file_info["basename"],
        channels=channel_list
    )
    outfile = open(export_file_info["stripped_name"] + '.html', 'wb')
    outfile.write(html.encode('utf-8'))

def export_multi(archive, save_dir=None, cache_dir=None):
    """
    Export the entire archive directory into html files

    :param archive: path to the source zip file
    :type archive: str
    :param save_dir: path to the output directory
    :type save_dir: str
    :param cache_dir: path to the cache/tmp directory
    :type cache_dir: str

    """

    if cache_dir is None:
        cache_dir = os.path.join(os.getcwd(), "temp")
    os.environ["SLACKVIEWER_TEMP_PATH"] = os.path.join(cache_dir, "_slackviewer")

    tmpl = Environment(loader=PackageLoader('slackviewer')).get_template("export_multi.html")
    export_file_info = get_export_info(archive)
    r = Reader(export_file_info["readable_path"])
    channel_list = sorted(
        [{"channel_name": k, "messages": v} for (k, v) in r.compile_channels().items()],
        key=lambda d: d["channel_name"]
    )

    # save dir
    if save_dir is None:
        save_dir = os.path.join(os.getcwd(), "out", "static")
    else:
        save_dir = os.path.join(save_dir, "out", "static")
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)
    # copy css
    css_path = os.path.join(save_dir, "viewer.css")
    if not os.path.exists(css_path):
        current_path = os.path.dirname(os.path.realpath(__file__))
        css_src = os.path.join(current_path, "static", "viewer.css")
        shutil.copyfile(src=css_src, dst=css_path)

    # get channel names
    channel_names = list()
    for channel in channel_list:
        channel_names.append(channel.get("channel_name"))

    for channel in channel_list:
        print("channel: " + str(channel.get("channel_name")))
        html = tmpl.render(
            generated_on=datetime.now(),
            workspace_name=export_file_info["workspace_name"],
            source_file=export_file_info["basename"],
            channel_names=channel_names,
            channel=channel
        )
        save_filename = channel.get("channel_name") + ".html"
        outfile = open(os.path.join(save_dir, save_filename), 'wb')
        outfile.write(html.encode('utf-8'))

    # copying downloaded files from cache
    file_dir_cache = os.path.join(export_file_info.get("readable_path"), "files")
    file_dir_dest = os.path.join(save_dir, "files")
    if not os.path.exists(file_dir_dest):
        os.makedirs(file_dir_dest)
    shutil.copytree(file_dir_cache, file_dir_dest, dirs_exist_ok=True)

    # delete cache/temp dir
    shutil.rmtree(cache_dir)
