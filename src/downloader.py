import requests
from urllib.parse import quote
import sys
import os
from datetime import datetime
from exif import Image
import json
from typing import Any


def create_folder_if_not_exists(folder_path: str) -> None:
    """Create a folder if it does not exist.

    Args:
        folder_path (str): The path to the folder to be created.
    """
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)


def get_children_data(access_token: str) -> list[dict[str, Any]]:
    """Retrieve children data from the API.

    Args:
        access_token (str): The access token for API authentication.

    Returns:
        list[dict[str, Any]]: A list of children data.
    """
    headers = {
        'authority': 'app.famly.co',
        'accept': '*/*',
        'accept-language': 'en-GB,en;q=0.9,es-VE;q=0.8,es;q=0.7,en-US;q=0.6',
        'content-type': 'application/json',
        'dnt': '1',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"macOS"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'x-famly-accesstoken': access_token,
        'x-famly-route': '/account/childProfile/:childId/activity',
        'x-famly-version': '43fc96ddd2'
    }

    response = requests.get(
        'https://app.famly.co/api/v2/calendar/list', headers=headers)

    return response.json()['children']


def fetch_tagged_image_metadata(access_token: str, limit: int, child_id: str, created_at: str | None = None, cutoff_date: str | None = None) -> list[dict[str, Any]]:
    """Fetch metadata for images tagged with a child's ID.

    Args:
        access_token (str): The access token for API authentication.
        limit (int): The maximum number of items to fetch.
        child_id (str): The ID of the child.
        created_at (str | None): The timestamp to fetch images created before.
        cutoff_date (str | None): The cutoff date to stop fetching images.

    Returns:
        list[dict[str, Any]]: A list of image metadata.
    """
    parsed_cutoff_date = None
    if cutoff_date:
        parsed_cutoff_date = datetime.fromisoformat(cutoff_date)
    url = f"https://app.famly.co/api/v2/images/tagged?childId={
        child_id}&limit={limit}"
    if created_at:
        url = f"{url}&olderThan={quote(created_at)}"

    headers = {
        'authority': 'app.famly.co',
        'accept': '*/*',
        'accept-language': 'en-GB,en;q=0.9,es-VE;q=0.8,es;q=0.7,en-US;q=0.6',
        'content-type': 'application/json',
        'dnt': '1',
        'sec-ch-ua': '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"macOS"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'x-famly-accesstoken': access_token,
        'x-famly-platform': 'html',
    }

    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        data = response.json()
        if (len(data) >= limit) and (parsed_cutoff_date is None or parsed_cutoff_date < datetime.fromisoformat(data[-1]['createdAt'])):
            print(f"Got more than {
                  limit} items, we'll want to attempt to fetch the next page")
            return data + fetch_tagged_image_metadata(access_token, limit, child_id, data[-1]["createdAt"])
        else:
            return [d for d in data if parsed_cutoff_date is None or datetime.fromisoformat(d['createdAt']) > parsed_cutoff_date]

    else:
        print(f"Failed to retrieve data: {response.status_code}")
        return []


def update_exif_date(image_path: str, new_date: datetime) -> None:
    """Update the EXIF date of an image.

    Args:
        image_path (str): The file path of the image.
        new_date (datetime): The new date to set in the image's EXIF data.
    """    # Open the image file for reading (binary mode)
    with open(image_path, 'rb') as image_file:
        img = Image(image_file)

    # Check if the image has EXIF data
    if img.has_exif:
        # Convert the new date to the EXIF date format: "YYYY:MM:DD HH:MM:SS"
        formatted_date = new_date.strftime("%Y:%m:%d %H:%M:%S")

        # Update EXIF date fields
        img.datetime_original = formatted_date
        img.datetime_digitized = formatted_date

        # Write the changes back to the file
        with open(image_path, 'wb') as image_file:
            image_file.write(img.get_file())


def download_image(image: dict[str, Any], path: str) -> None:
    """Download an image and update its EXIF date.

    Args:
        image (dict[str, Any]): The image metadata.
        path (str): The path where the image will be saved.
    """
    response = requests.get(image["url_big"])

    # Check if the request was successful
    if response.status_code == 200:
        # Open a file in binary write mode
        image_path = f"{path}/{image["imageId"]}.jpg"
        with open(image_path, "wb") as file:
            # Write the content of the response to the file
            file.write(response.content)
            update_exif_date(
                image_path, datetime.fromisoformat(image['createdAt']))


def print_progress_bar(iteration: int, total: int, prefix: str = '', suffix: str = '', decimals: int = 1, length: int = 50, fill: str = '█') -> None:
    """Print a progress bar to the console.

    Args:
        iteration (int): Current iteration number.
        total (int): Total iterations.
        prefix (str): Prefix string.
        suffix (str): Suffix string.
        decimals (int): Positive number
        length (int): Length of the progress bar.
        fill (str): Fill character.
    """

    percent = ("{0:." + str(decimals) + "f}").format(100 *
                                                     (iteration / float(total)))
    filled_length = int(length * iteration // total)
    bar = fill * filled_length + '-' * (length - filled_length)
    sys.stdout.write(f'\r{prefix} |{bar}| {
                     percent}%  ({iteration}/{total}) {suffix}')
    sys.stdout.flush()


def get_all_images_for_child(access_token: str, items_per_request: int, child_id: str, child_name: str, cutoff_date: str, settings: dict[str, Any]) -> None:
    """
    Fetches all tagged image metadata for a given child and downloads the images.

    :param access_token: The access token for authentication.
    :param items_per_request: The number of items to fetch per request.
    :param child_id: The unique identifier for the child.
    :param child_name: The name of the child.
    :param cutoff_date: The date to fetch images up to.
    :param settings: A dictionary containing settings such as metadata path.
    """
    images = fetch_tagged_image_metadata(
        access_token, items_per_request, child_id, cutoff_date=cutoff_date)

    if not images:
        print(f"No new images for {child_name}")
        return

    print(f"Starting download for {len(images)} images")
    img_count = len(images)

    for i in range(img_count):
        image = images[i]
        parsed_date = datetime.fromisoformat(image['createdAt'])
        path = f"out/images/{child_name}/{parsed_date.year}/{
            parsed_date.month}"
        create_folder_if_not_exists(path)
        download_image(image, path)
        print_progress_bar(i + 1, img_count, prefix='Progress:',
                           suffix='Complete', length=50)

    write_metadata_file(settings['metadata_path'], images[0]['createdAt'])


def load_json_file(file_path: str) -> Any:
    """
    Loads a JSON file from the given file path.

    :param file_path: The path to the JSON file to be loaded.
    :return: The content of the JSON file.
    :raises ValueError: If the file does not exist at the specified path.
    """
    if not os.path.exists(file_path):
        raise ValueError(f"Settings file not found at {
                         file_path}. Please copy .env.json to .env.local.json and replace the relevant values")
    with open(file_path, 'r', encoding='utf-8') as file:
        return json.load(file)


def get_or_create_metadata_file(path: str) -> dict[str, Any]:
    """
    Gets the metadata file from the given path, or creates it if it does not exist.

    :param path: The path to the metadata file.
    :return: The content of the metadata file.
    """
    if not os.path.exists(path):
        with open(path, 'w') as file:
            json.dump({}, file)
    return load_json_file(path)


def write_metadata_file(path: str, cutoff_date: str) -> None:
    """
    Writes the cutoff date to the metadata file at the given path.

    :param path: The path to the metadata file.
    :param cutoff_date: The cutoff date to be written to the file.
    """
    with open(path, 'w') as file:
        json.dump({"cutoff_date": cutoff_date}, file)


def main():
    settings = load_json_file(".env.local.json")
    token = settings['access_token']
    metadata = get_or_create_metadata_file(settings['metadata_path'])

    children = get_children_data(token)

    for child in children:
        get_all_images_for_child(
            token, settings['items_per_request'], child['childId'], child['name'], metadata.get('cutoff_date'), settings)


if __name__ == "__main__":
    main()
