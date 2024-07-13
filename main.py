from urllib.parse import urlparse, parse_qsl
import requests
import json
import re
import random
from requests.exceptions import HTTPError
from datetime import datetime, timezone
from typing import List, Dict
import threading
import time

lock = threading.Lock()


HEADERS = {
            "User-Agent": "PostmanRuntime/7.28.4",  # random.choice(USER_AGENTS),
            "Host": "www.vinted.co.uk",
}

MAX_RETRIES = 3
class Requester:


    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self.VINTED_AUTH_URL = f"https://www.vinted.co.uk/auth/token_refresh"
        #self.setCookies()



    def get(self, url, params=None):
        """
        Perform a http get request.
        :param url: str
        :param params: dict, optional
        :return: dict
            Json format
        """
        tried = 0
        while tried < MAX_RETRIES:
            tried += 1
            with self.session.get(url, params=params) as response:

                if response.status_code == 401 and tried < MAX_RETRIES:
                    print(f"Cokkies invalid retrying {tried}/{MAX_RETRIES}")
                    self.setCookies()

                elif response.status_code == 200 or tried == MAX_RETRIES:
                    return response


        return HTTPError

    def post(self,url, params=None):
        response = self.session.post(url, params)
        response.raise_for_status()
        return response

    def setCookies(self):


        self.session.cookies.clear_session_cookies()


        try:

            self.post(self.VINTED_AUTH_URL)
            print("Cookies set!")

        except Exception as e:
            print(
                f"There was an error fetching cookies for vinted\n Error : {e}"
            )

requester = Requester()


class Item:
    def __init__(self, data):
        self.raw_data = data
        self.id = data["id"]
        self.title = data["title"]
        self.brand_title = data["brand_title"]
        try:
            self.size_title = data["size_title"]
        except:
            self.size_title = data["size_title"]
        self.currency = data["currency"]
        self.price = data["price"]
        self.photo = data["photo"]["url"]
        self.url = data["url"]
        self.created_at_ts = datetime.fromtimestamp(
            data["photo"]["high_resolution"]["timestamp"], tz=timezone.utc
        )
        self.raw_timestamp = data["photo"]["high_resolution"]["timestamp"]
        self.condition = data['status']

    def __eq__(self, other):
        return self.id == other.id

    def __hash__(self):
        return hash(('id', self.id))

    def isNewItem(self, minutes=3):
        delta = datetime.now(timezone.utc) - self.created_at_ts
        return delta.total_seconds() < minutes * 60

class Items:
    def search(self, url, nbrItems: int = 20, page: int =1, time: int = None, json: bool = False) -> List[Item]:
        """
        Retrieves items from a given search url on vited.

        Args:
            url (str): The url of the research on vinted.
            nbrItems (int): Number of items to be returned (default 20).
            page (int): Page number to be returned (default 1).

        """

        params = self.parseUrl(url, nbrItems, page, time)
        url = f"{Urls.VINTED_API_URL}/{Urls.VINTED_PRODUCTS_ENDPOINT}"

        try:
            response = requester.get(url=url, params=params)
            response.raise_for_status()
            items = response.json()
            items = items["items"]
            if not json:
                return [Item(_item) for _item in items]
            else:
                return items

        except HTTPError as err:
            raise err


    def parseUrl(self, url, nbrItems=20, page=1, time=None) -> Dict:
        """
        Parse Vinted search url to get parameters the for api call.

        Args:
            url (str): The url of the research on vinted.
            nbrItems (int): Number of items to be returned (default 20).
            page (int): Page number to be returned (default 1).

        """
        querys = parse_qsl(urlparse(url).query)

        params = {
            "search_text": "+".join(
                map(str, [tpl[1] for tpl in querys if tpl[0] == "search_text"])
            ),
            "catalog_ids": ",".join(
                map(str, [tpl[1] for tpl in querys if tpl[0] == "catalog[]"])
            ),
            "color_ids": ",".join(
                map(str, [tpl[1] for tpl in querys if tpl[0] == "color_ids[]"])
            ),
            "brand_ids": ",".join(
                map(str, [tpl[1] for tpl in querys if tpl[0] == "brand_ids[]"])
            ),
            "size_ids": ",".join(
                map(str, [tpl[1] for tpl in querys if tpl[0] == "size_ids[]"])
            ),
            "material_ids": ",".join(
                map(str, [tpl[1] for tpl in querys if tpl[0] == "material_ids[]"])
            ),
            "status_ids": ",".join(
                map(str, [tpl[1] for tpl in querys if tpl[0] == "status[]"])
            ),
            "country_ids": ",".join(
                map(str, [tpl[1] for tpl in querys if tpl[0] == "country_ids[]"])
            ),
            "city_ids": ",".join(
                map(str, [tpl[1] for tpl in querys if tpl[0] == "city_ids[]"])
            ),
            "is_for_swap": ",".join(
                map(str, [1 for tpl in querys if tpl[0] == "disposal[]"])
            ),
            "currency": ",".join(
                map(str, [tpl[1] for tpl in querys if tpl[0] == "currency"])
            ),
            "price_to": ",".join(
                map(str, [tpl[1] for tpl in querys if tpl[0] == "price_to"])
            ),
            "price_from": ",".join(
                map(str, [tpl[1] for tpl in querys if tpl[0] == "price_from"])
            ),
            "page": page,
            "per_page": nbrItems,
            "order": ",".join(
                map(str, [tpl[1] for tpl in querys if tpl[0] == "order"])
            ),
            "time": time
        }

        return params


class Urls:
    VINTED_API_URL = f"https://www.vinted.co.uk/api/v2"
    VINTED_PRODUCTS_ENDPOINT = "catalog/items"

class Vinted:
    """
    This class is built to connect with the pyVinted API.

    It's main goal is to be able to retrieve items from a given url search.\n

    """

    def __init__(self, proxy=None):
        """
        Args:
            Proxy : proxy to be used to bypass vinted's limite rate

        """

        if proxy is not None:
            requester.session.proxies.update(proxy)

        self.items = Items()


def sendWebhook(latestItem, url):
    data = {
        "username" : "Vinted Monitor",
        "avatar_url": "https://cdn.discordapp.com/attachments/1134875841587859557/1134876571837145188/White_BG_Logo.png?ex=6690002b&is=668eaeab&hm=eb1fac08ae5163c6373dd235fd0e5f26f81191c83fc29868893bc915bc19c351&",
        "embeds" : [] 
    }

    data["embeds"] = [
        {
            "title" : latestItem.title,
            "url": latestItem.url,
            "color": 16777215,
            "fields": [
            {
              "name": ":moneybag: Price",
              "value": "> £" + str(latestItem.price) + '0',
              "inline": True
            },
            {
              "name": ":straight_ruler: Size",
              "value": "> " + latestItem.size_title,
              "inline": True
            },
            {
              "name": ":label: Brand",
              "value": "> " + latestItem.brand_title,
              "inline": True
            },
            {
              "name": ":fire: Condition",
              "value": "> " + latestItem.condition,
              "inline": True
            },
            {
              "name": ":link: Vinted Link",
              "value": f"[View Listing]({latestItem.url})"
            },
            {  

              "name": ":link: Ebay Link",
              "value": f"[Link](https://www.ebay.co.uk/sch/i.html?_from=R40&_trksid=p2334524.m570.l1313&_nkw={latestItem.title.replace(' ', '+')})"
            }
          ],
            "author": {
                "name": "Humza's Monitors",
                "icon_url": "https://cdn.discordapp.com/attachments/1134875841587859557/1134876571837145188/White_BG_Logo.png?ex=6690002b&is=668eaeab&hm=eb1fac08ae5163c6373dd235fd0e5f26f81191c83fc29868893bc915bc19c351&"
              },
            "footer": {
                "text": "Humza's FNF",
                "icon_url": "https://cdn.discordapp.com/attachments/1134875841587859557/1134876571837145188/White_BG_Logo.png?ex=6690002b&is=668eaeab&hm=eb1fac08ae5163c6373dd235fd0e5f26f81191c83fc29868893bc915bc19c351&"
              },
            "image": {
                "url": latestItem.photo
              }

        }
    ]

    result = requests.post(url, json = data)

    try:
        result.raise_for_status()
    except requests.exceptions.HTTPError as err:
        print(err)
    else:
        print(f"Payload delivered successfully, code {result.status_code}.")


val = ''
val2 = ''
val3 = ''
lastItem = ''
lastItem2 = ''
lastItem3 = ''
def main():
    with lock:
        global val
        global val2 
        global val3
        global lastItem
        global lastItem2
        global lastItem3
        
        vinted = Vinted()
        
        items = vinted.items.search("https://www.vinted.co.uk/catalog?search_text=Nike&order=newest_first",1,1)
        items2 = vinted.items.search("https://www.vinted.co.uk/catalog?search_text=sb%20dunks&order=newest_first&brand_ids[]=283953",1,1)
        items3 = vinted.items.search("https://www.vinted.co.uk/catalog?search_text=Nike%20off%20white&order=newest_first&brand_ids[]=5750136",1,1)

        if items and items2 and items3:
            latestItem = items[0]
            latestItem2 = items2[0]
            latestItem3 = items3[0]
        else:
            return
        
        if val == None:
            print('Monitor live')
            print(latestItem.title)
        elif val != latestItem.url and lastItem != latestItem.title and lastItem2 != latestItem.title and lastItem3 != latestItem.title:
            print(latestItem.title)
            url = "https://canary.discord.com/api/webhooks/1261815711945326654/cPEQHGddruahBQlbkPDnc0HD_Z7XCs5_ZfA8zAh88Z0rVfv6zbbyq_l4u61NRI4I5YJM"
            sendWebhook(latestItem, url)
            lastItem = latestItem.title
        if val2 != latestItem2.url and lastItem != latestItem2.title and lastItem2 != latestItem2.title and lastItem3 != latestItem2.title:
            print(latestItem2.title)
            url = "https://canary.discord.com/api/webhooks/1261815711945326654/cPEQHGddruahBQlbkPDnc0HD_Z7XCs5_ZfA8zAh88Z0rVfv6zbbyq_l4u61NRI4I5YJM"
            sendWebhook(latestItem2, url)   
            lastItem2 = latestItem2.title
        if val3 != latestItem3.url and lastItem != latestItem3.title and lastItem2 != latestItem3.title and lastItem3 != latestItem3.title:
            print(latestItem3.title)
            url = "https://canary.discord.com/api/webhooks/1261815711945326654/cPEQHGddruahBQlbkPDnc0HD_Z7XCs5_ZfA8zAh88Z0rVfv6zbbyq_l4u61NRI4I5YJM"
            sendWebhook(latestItem3, url)   
            lastItem3 = latestItem3.title

        val = latestItem.url
        val2 = latestItem2.url
        val3 = latestItem3.url
        time.sleep(10)
        
while True:
    main()



'''
https://canary.discord.com/api/webhooks/1258431841451511809/-A9gALygTkR46PoPfwPPrCBDUXSzfcFyWWqiM62skioVfRaq6n3iNIGwi9qiHuDHxT9Y
'''
