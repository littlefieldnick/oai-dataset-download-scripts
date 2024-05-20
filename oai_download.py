import base64
import requests
import json
import urllib.request
import shutil
from pathlib import Path

import configparser

configs = configparser.ConfigParser()
configs.read('oai_tools.ini')

# Encode our credentials then convert it to a string.
credentials_str = f'{configs["NIH-CREDENTIALS"]["username"]}:{configs["NIH-CREDENTIALS"]["password"]}'
credentials = base64.b64encode(bytes(credentials_str, 'utf-8')).decode('utf-8')

# Create the headers we will be using for all requests.
headers = {
    'Authorization': 'Basic ' + credentials,
    'User-Agent': 'Example Client',
    'Accept': 'application/json'
}

# Send Http request
response = requests.get('https://nda.nih.gov/api/package/auth', headers=headers)

# If the response status code does not equal 200
# throw an exception up.
if response.status_code != requests.codes.ok:
    print('failed to authenticate')
    response.raise_for_status()
else:
    print("passed authentication")

packageNameKeys = configs["PACKAGE-INFO"].keys()

for package in packageNameKeys:
    packageId = configs["PACKAGE-INFO"][package]
    # URL structure is: https://nda.nih.gov/api/package/{packageId}/files
    response = requests.get('https://nda.nih.gov/api/package/' + str(packageId) + '/files', headers=headers)

    # Get the results array from the json response.
    results = response.json()['results']

    files = {}

    # Add important file data to the files dictionary.
    for f in results:
        files[f['package_file_id']] = {'name': f['download_alias']}

    # Create a post request to the batch generate presigned urls endpoint.
    # Use keys from files dictionary to form a list, which is converted to
    # a json array which is posted.
    response = requests.post('https://nda.nih.gov/api/package/' + str(packageId) + '/files/batchGeneratePresignedUrls',
                             json=list(files.keys()), headers=headers)

    # Get the presigned urls from the response.
    results = response.json()['presignedUrls']

    # Add a download key to the file's data.
    for url in results:
        files[url['package_file_id']]['download'] = url['downloadURL']

    # Iterate on file id and it's data to perform the downloads.
    for id, data in files.items():
        name = data['name']
        downloadUrl = data['download']

        # Create a downloads directory
        file = f'{configs["OUT-DIR"]["path"]}/{package}/' + name

        # Strip out the file's name for creating non-existent directories
        directory = file[:file.rfind('/')]

        # Create non-existent directories, package files have their
        # own directory structure, and this will ensure that it is
        # kept in tact when downloading.
        Path(directory).mkdir(parents=True, exist_ok=True)

        # Initiate the download.
        with urllib.request.urlopen(downloadUrl) as dl, open(file, 'wb') as out_file:
            print("Writing to:", out_file.name)
            shutil.copyfileobj(dl, out_file)

        print("Finished writing to", out_file.name)


