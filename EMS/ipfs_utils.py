import requests

PINATA_API_KEY ="dd33d8eae2a8137abf03"
PINATA_SECRET_API_KEY ="8a86e92c856529a94d9bfee39fc22483768b438baf92fe4756f228404a616a39"
def upload_to_pinata(file):
    url = "https://api.pinata.cloud/pinning/pinFileToIPFS"
    headers = {
        "pinata_api_key": PINATA_API_KEY,
        "pinata_secret_api_key": PINATA_SECRET_API_KEY
    }
    files = {'file': (file.name, file)}
    response = requests.post(url, files=files, headers=headers)

    if response.status_code == 200:
        ipfs_hash = response.json()['IpfsHash']
        return f"https://gateway.pinata.cloud/ipfs/{ipfs_hash}", ipfs_hash
    else:
        raise Exception(f"Pinata upload failed: {response.text}")
