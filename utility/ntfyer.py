import os

import requests
from dotenv import load_dotenv
from requests.auth import HTTPBasicAuth

from utility import config


def ntfy(data: str, title: str):
    """ Send a ntfy message to the server """

    load_dotenv()
    if config.ENABLE_NTFYER:
        requests.post(f"{os.getenv('NTFY_URL')}/{os.getenv('NTFY_TOPIC')}",
                      data=data,
                      headers={
                          "Title": title
                      },
                      auth=HTTPBasicAuth(os.getenv("NTFY_USERNAME"), os.getenv("NTFY_PASSWORD"))
                      )
