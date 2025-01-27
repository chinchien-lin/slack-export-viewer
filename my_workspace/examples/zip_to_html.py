from pathlib import Path
from slackviewer.export import export_multi, export

if __name__ == '__main__':
    # export multiple
    source = Path(
        r"/path/to/exported_zip_file.zip")
    dest = Path(r"/output_dir")

    export_multi(archive=str(source), save_dir=str(dest))

    # export single
    # source = Path(r"C:\Users\clin864\OneDrive - The University of Auckland\my-projects\slack\slack-export-viewer\my_workspace\test_data\ABI Clinical Translational Technologies Group Slack export Jun 1 2024 - Jun 30 2024")
    # export(source)

    print("completed")



