import requests
from urllib.parse import quote
import sys
import os
from datetime import datetime
from exif import Image

ITEMS_PER_REQUEST = 2000
ACCESS_TOKEN = "<ACCESS_TOKEN>"


def create_folder_if_not_exists(folder_path):
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)


def get_children_data():
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
        'x-famly-accesstoken': ACCESS_TOKEN,
        'x-famly-route': '/account/childProfile/:childId/activity',
        'x-famly-version': '43fc96ddd2'
    }

    response = requests.get(
        'https://app.famly.co/api/v2/calendar/list', headers=headers)

    return response.json()['children']


def fetch_tagged_image_metadata(limit, child_id, created_at=None):
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
        'x-famly-accesstoken': ACCESS_TOKEN,
        'x-famly-platform': 'html',
    }

    response = requests.get(url, headers=headers)

    # To handle the response, you might want to check if the request was successful
    if response.status_code == 200:
        # If you expect a JSON response, you can use response.json()
        data = response.json()
        print(f"Got {len(data)} items")
        # Do something with the data
        if (len(data) >= limit):
            print(f"Got more than {
                  limit} items, we'll want to attempt to fetch the next page")
            return data + fetch_tagged_image_metadata(limit, child_id, data[-1]["createdAt"])
        else:
            return data

    else:
        print(f"Failed to retrieve data: {response.status_code}")
        return []


def update_exif_date(image_path, new_date):
    # Open the image file for reading (binary mode)
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


def download_image(image, path):
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


def print_progress_bar(iteration, total, prefix='', suffix='', decimals=1, length=50, fill='█'):
    percent = ("{0:." + str(decimals) + "f}").format(100 *
                                                     (iteration / float(total)))
    filled_length = int(length * iteration // total)
    bar = fill * filled_length + '-' * (length - filled_length)
    sys.stdout.write(f'\r{prefix} |{bar}| {
                     percent}%  ({iteration}/{total}) {suffix}')
    sys.stdout.flush()


def get_all_images_for_child(child_id, child_name):
    images = fetch_tagged_image_metadata(ITEMS_PER_REQUEST, child_id)
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


children = get_children_data()
for child in children:
    get_all_images_for_child(child['childId'], child['name'])
