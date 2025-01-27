import hashlib
import json
import os
import zipfile
import io

from os.path import basename, splitext

from pathlib import Path
import requests

import slackviewer
from slackviewer.constants import SLACKVIEWER_TEMP_PATH
from slackviewer.utils.six import to_unicode, to_bytes

from urllib.parse import urlparse


def truncate_path(path):
    # max length for path separator between parent and name: 2 (Windows)
    max_len = 260 - 2

    if len(str(path)) > max_len:
        stem_len = max_len - len(str(path.parent)) - len(path.suffix)
        filename_truncated = path.stem[:stem_len]
        new_path = path.parent.joinpath(filename_truncated + path.suffix)
        path = new_path

    return Path(path)

def download_file(url, local_file):
    # Send an HTTP request to the given URL
    with requests.get(url, stream=True) as r:
        # Raise an HTTPError for bad responses
        r.raise_for_status()

        with open(local_file, 'wb') as f:
            # Write the content to the local file in chunks
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)

    return local_file


def get_all_json_files_recursively(directory):
    json_file_list = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.json'):
                json_file_list.append(os.path.join(root, file))
    return json_file_list


def SHA1_file(filepath, extra=b''):
    """
    Returns hex digest of SHA1 hash of file at filepath

    :param str filepath: File to hash

    :param bytes extra: Extra content added to raw read of file before taking hash

    :return: hex digest of hash

    :rtype: str
    """
    h = hashlib.sha1()
    with io.open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(h.block_size), b''):
            h.update(chunk)
    h.update(extra)
    return h.hexdigest()


def extract_archive(filepath):
def download_files(data, files, item_idx, dest_dir):
    """
    Downloads & saves files

    :param data: The data containing the files information.
    :type data: list
    :param files: The list of files to be downloaded.
    :type files: list
    :param item_idx: The index of the current item in the data list.
    :type item_idx: int
    :param dest_dir: The destination directory where files will be saved.
    :type dest_dir: pathlib.Path
    """
    dest_dir = dest_dir.joinpath("files")
    dest_dir.mkdir(exist_ok=True)

    if not files:
        return

    for file_idx, file in enumerate(files):
        is_external = file.get("is_external")
        if is_external:
            continue

        mode = file.get("mode")
        if mode and mode in ["hidden_by_limit", "tombstone"]:
            continue

        name = file.get("name")

        user_team = file.get("user_team")
        id = file.get("id")
        file_id = user_team + "-" + id

        # url_fields = ["url_private", "url_private_download", "thumb_pdf", "permalink", "permalink_public"]
        url_fields = ["url_private", "url_private_download", "thumb_pdf"]

        for url_field in url_fields:
            url = file.get(url_field)
            if url:
                file_path = dest_dir.joinpath(file_id,  url_field, name)

                file_path = truncate_path(file_path)

                print("file_path: " + str(file_path))
                file_path.parent.mkdir(parents=True, exist_ok=True)
                download_file(url, str(file_path))
                # replace remote url with local url
                base_path = file_path.parent.parent.parent.parent.parent
                file_path_relative = file_path.relative_to(base_path)
                data[item_idx]["files"][file_idx][url_field] = str(file_path_relative)

                print("Remote URL - " + url_field + ": " + str(url))
                print("local URL: " + str(file_path_relative))
def extract_archive(filepath, extracted_path=None):
    """
    Returns the path of the archive

    :param str filepath: Path to file to extract or read

    :param str extracted_path: path of the archive

    :return: path of the archive

    :rtype: str
    """

    # Checks if file path is a directory
    if os.path.isdir(filepath):
        path = os.path.abspath(filepath)
        print("Archive already extracted. Viewing from {}...".format(path))
        return path

    # Checks if the filepath is a zipfile and continues to extract if it is
    # if not it raises an error
    elif not zipfile.is_zipfile(filepath):
        # Misuse of TypeError? :P
        raise TypeError("{} is not a zipfile".format(filepath))

    archive_sha = SHA1_file(
        filepath=filepath,
        # Add version of slackviewer to hash as well so we can invalidate the cached copy
        #  if there are new features added
        extra=to_bytes(slackviewer.__version__)
    )

    if not extracted_path:
        try:
            extracted_path = os.path.join(os.getenv('SLACKVIEWER_TEMP_PATH'), archive_sha)
        except:
            extracted_path = os.path.join(SLACKVIEWER_TEMP_PATH, archive_sha)

    if os.path.exists(extracted_path):
        print("{} already exists".format(extracted_path))
    else:
        # Extract zip
        with zipfile.ZipFile(filepath) as zip:
            print("{} extracting to {}...".format(filepath, extracted_path))
            for info in zip.infolist():
                print(info.filename)
                info.filename = info.filename.encode("cp437").decode("utf-8")
                print(info.filename)
                zip.extract(info,path=extracted_path)

        print("{} extracted to {}".format(filepath, extracted_path))

        # Add additional file with archive info
        create_archive_info(filepath, extracted_path, archive_sha)

    # download
    dest_dir = Path(extracted_path)
    file_dir = dest_dir.joinpath("files")
    file_dir.mkdir(exist_ok=True)

    # excluded_files = [".slackviewer_archive_info.json", "canvases.json", "channels.json", "huddle_transcripts.json", "integration_logs.json", "lists.json", "users.json"]
    excluded_files = [".slackviewer_archive_info.json", "canvases.json", "channels.json", "huddle_transcripts.json",
                      "integration_logs.json", "lists.json"]
    json_files = get_all_json_files_recursively(extracted_path)
    for json_file in json_files:
        if any(excluded_file in json_file for excluded_file in excluded_files):
            continue
        print("processing " + str(json_file))
        with open(json_file, "r", encoding="cp866") as f:
            data = json.load(f)


        for item_idx, item in enumerate(data):
            download_files(data, item.get("files"), item_idx, file_dir)

        with open(json_file, "w") as f:
            json.dump(data, f)

    return extracted_path


# Saves archive info
# When loading empty dms and there is no info file then this is called to
# create a new archive file
def create_archive_info(filepath, extracted_path, archive_sha=None):
    """
    Saves archive info to a json file

    :param str filepath: Path to directory of archive

    :param str extracted_path: Path to directory of archive

    :param str archive_sha: SHA string created when archive was extracted from zip
    """

    archive_info = {
        "sha1": archive_sha,
        "filename": os.path.split(filepath)[1],
    }

    with io.open(
        os.path.join(
            extracted_path,
            ".slackviewer_archive_info.json",
        ), 'w+', encoding="utf-8"
    ) as f:
        s = json.dumps(archive_info, ensure_ascii=False)
        s = to_unicode(s)
        f.write(s)


def get_export_info(archive_name):
    """
    Given a file or directory, extract it and return information that will be used in
    an export printout: the basename of the file, the name stripped of its extension, and
    our best guess (based on Slack's current naming convention) of the name of the
    workspace that this is an export of.
    """
    extracted_path = extract_archive(archive_name)
    base_filename = basename(archive_name)
    (noext_filename, _) = splitext(base_filename)
    # Typical extract name: "My Friends and Family Slack export Jul 21 2018 - Sep 06 2018"
    # If that's not the format, we will just fall back to the extension-free filename.
    (workspace_name, _) = noext_filename.split(" Slack export ", 1)
    return {
        "readable_path": extracted_path,
        "basename": base_filename,
        "stripped_name": noext_filename,
        "workspace_name": workspace_name,
    }
