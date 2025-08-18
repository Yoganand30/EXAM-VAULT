import requests
from django.conf import settings

IPFS_API_URL = f"http://{settings.IPFS_HOST}:{settings.IPFS_PORT}/api/v0"

def add_file(path):
    """
    Upload a file to IPFS via HTTP API.
    Returns the 'Hash' field from the JSON response.
    """
    with open(path, 'rb') as f:
        files = {'file': f}
        res = requests.post(f"{IPFS_API_URL}/add", files=files)
    res.raise_for_status()
    return res.json()  # contains 'Name' and 'Hash'

def get_file(cid):
    """
    Retrieve raw file bytes from IPFS via HTTP API.
    """
    res = requests.post(f"{IPFS_API_URL}/cat?arg={cid}")
    res.raise_for_status()
    return res.content
