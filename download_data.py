from pathlib import Path, PurePath
import configparser
import os
import requests
from zipfile import ZipFile
import logging

logging.basicConfig(
    level=logging.INFO, format="%(levelname)-7s  %(name)-19s  %(message)s", style="%"
)
logger = logging.getLogger("CourseHandler")

# CONFIGURATIONS / SET UP
REPO_PATH = Path(__file__).resolve().parent
# Extract download path for Data Sets
DATA_SETS_PATH = REPO_PATH / "data-sets"
WORK_PATH = REPO_PATH / "work"
# Set chunk size for downloading (avoid unnecessary loading to memory)
CHUNK_SIZE = 5242880  # 5 MB in bytes
# Name/location of the data_sets configuration file
CONFIG_LOCATION = REPO_PATH / "conf" / "data_sets.conf"


def create_dir_if_not_exists(dir_path):
    if not os.path.exists(dir_path):
        logger.info("Creating %s directory", PurePath(dir_path).name)
        os.makedirs(dir_path)


def path_already_exists(dir_path):
    if os.path.exists(dir_path):
        logger.info('Directory "%s" already exists', PurePath(dir_path).name)
        return True
    else:
        return False


def download():
    # Create data-sets folder if it does not yet exist
    create_dir_if_not_exists(DATA_SETS_PATH)

    # PROCESSING DATA SETS DEFINED IN CONFIGURATION FILE
    config = configparser.ConfigParser()
    config.read(str(CONFIG_LOCATION))

    for section in config.sections():
        logger.info("Processing {}".format(section))
        readme_md = None

        # Parse configuration for data_set
        data_set_config = config[section]
        download_path = data_set_config["download_path"]
        filename = data_set_config["filename"]
        has_readme = data_set_config.get("has_readme") == "True"
        destination_path = data_set_config.get("destination_path")
        if not has_readme:
            readme_location = data_set_config["readme_location"]
            license_info = data_set_config["license_info"]
            readme_md = "readme_location: {readme_location}\nlicense_info: {license_info}".format(
                readme_location=readme_location, license_info=license_info
            )

        # Set download locations
        if destination_path:
            destination_path = DATA_SETS_PATH / destination_path
            destination_downloadpath = destination_path
            destination_filepath = destination_path / filename
        else:
            destination_path = DATA_SETS_PATH
            destination_filepath = PurePath(destination_path / filename)
            destination_downloadpath = str(destination_filepath).replace(
                destination_filepath.suffix, ""
            )

        # To avoid compatibility issues downstream, set destination_filepath as string
        destination_filepath = str(destination_filepath)

        # Check if data is already downloaded
        if path_already_exists(destination_downloadpath):
            logger.info('Skipping "%s"', filename)
            continue

        # Create Directory
        create_dir_if_not_exists(destination_path)

        # Create README.MD file (if needed)
        if readme_md:
            readme_loc = str(destination_path / "README.md")
            with open(readme_loc, "wb") as readme:
                logger.info(" - Creating README.md file")
                readme.write(readme_md.encode("UTF-8"))

        # Download the file in chunks
        with requests.get(str(download_path), stream=True, verify=False) as r:
            r.raise_for_status()
            logger.info(
                'Downloading "%s" to "%s", this may take a few minutes',
                filename,
                destination_path,
            )
            with open(destination_filepath, "wb") as f:
                for chunk in r.iter_content(CHUNK_SIZE):
                    if chunk:  # filter out keep-alive chunks
                        f.write(chunk)
                    logger.info(
                        "%.0f MB downloaded...",
                        os.path.getsize(destination_filepath) / 1024 / 1024,
                    )
        logger.info("Finished downloading %s", filename)

        # Extract zipfile
        with ZipFile(destination_filepath, "r") as downloaded_file:
            logger.info(
                'Extracting "%s" to "%s"',
                downloaded_file.filename,
                destination_filepath,
            )
            downloaded_file.extractall(destination_path)

        # Remove zip file
        logger.info('Removing zip-file "%s"', filename)
        os.remove(destination_filepath)


if __name__ == "__main__":
    download()
