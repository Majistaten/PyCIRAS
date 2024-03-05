import os

import requests
from dotenv import load_dotenv
from requests.auth import HTTPBasicAuth


def ntfy(data: str, title: str):
    load_dotenv()
    requests.post(f"{os.getenv('NTFY_URL')}/{os.getenv('NTFY_TOPIC')}",
                  data=data,
                  headers={
                      "Title": title
                  },
                  auth=HTTPBasicAuth(os.getenv("NTFY_USERNAME"), os.getenv("NTFY_PASSWORD"))
                  )