import requests
import os

# Replace this with your actual file URL
url = "https://download.companieshouse.gov.uk/BasicCompanyData-2025-07-01-part1_7.zip"
# Replace this with your desired local filename
local_filename = "data/BasicCompanyData-2025-07-01-part1_7.zip"

# Ensure the 'data' directory exists
os.makedirs(os.path.dirname(local_filename), exist_ok=True)

with requests.get(url, stream=True) as r:
    r.raise_for_status()
    with open(local_filename, 'wb') as f:
        for chunk in r.iter_content(chunk_size=8192):
            f.write(chunk)

print(f"Download complete: {local_filename}")

# If the file is a zip file, extract its contents to the data folder
if local_filename.lower().endswith('.zip'):
    import zipfile
    with zipfile.ZipFile(local_filename, 'r') as zip_ref:
        zip_ref.extractall(os.path.dirname(local_filename))
    print(f"Extracted contents to: {os.path.dirname(local_filename)}")
    os.remove(local_filename)
    print(f"Deleted zip file: {local_filename}")
