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
from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home():
    return "<b>Never Settle.</b>"

def run():
  app.run(host='0.0.0.0',port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

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
val4 = ''
val5 = ''
val6 = ''
val7 = ''
val8 = ''
val9 = ''
val10 = ''
val11 = ''
val12 = ''
val13 = ''
val14 = ''
val15 = ''
val16 = ''
val17 = ''
val18 = '' 

lastItem = ''
lastItem2 = ''
lastItem3 = ''
lastItem4 = ''
lastItem5 = ''
lastItem6 = ''
lastItem7 = ''
lastItem8 = ''
lastItem9 = ''
lastItem10 = ''
lastItem11 = ''
lastItem12 = ''
lastItem13 = ''
lastItem14 = ''
lastItem15 = ''
lastItem16 = ''
lastItem17 = ''
lastItem18 = ''

def main():
    with lock:
        global val
        global val2 
        global val3
        global val4
        global val5
        global val6
        global val7
        global val8
        global val9
        global val10
        global val11
        global val12
        global val13
        global val14
        global val15 
        global val16
        global val17
        global val18 

        global lastItem
        global lastItem2
        global lastItem3
        global lastItem4
        global lastItem5
        global lastItem6
        global lastItem7
        global lastItem8
        global lastItem9
        global lastItem10
        global lastItem11
        global lastItem12
        global lastItem13
        global lastItem14
        global lastItem15 
        global lastItem16
        global lastItem17
        global lastItem18 

        vinted = Vinted()

        items = vinted.items.search("https://www.vinted.co.uk/catalog?search_text=Nike&order=newest_first",1,1)
        items2 = vinted.items.search("https://www.vinted.co.uk/catalog?search_text=sb%20dunks&order=newest_first&brand_ids[]=283953",1,1)
        items3 = vinted.items.search("https://www.vinted.co.uk/catalog?search_text=Nike%20off%20white&order=newest_first&brand_ids[]=5750136",1,1)

        items4 = vinted.items.search("https://www.vinted.co.uk/catalog?search_text=jordans%20&order=newest_first",1,1)
        items5 = vinted.items.search("https://www.vinted.co.uk/catalog?search_text=jordan%201s&order=newest_first",1,1)
        items6 = vinted.items.search("https://www.vinted.co.uk/catalog?search_text=jordan%204s&order=newest_first",1,1)

        items7 = vinted.items.search("https://www.vinted.co.uk/catalog?search_text=Yeezy&currency=GBP&order=newest_first&brand_ids[]=115490",1,1)
        items8 = vinted.items.search("https://www.vinted.co.uk/catalog?search_text=Yeezy%20350&currency=GBP&order=newest_first",1,1)
        items9 = vinted.items.search("https://www.vinted.co.uk/catalog?search_text=Yeezy%20700&currency=GBP&order=newest_first",1,1)
        items10 = vinted.items.search("https://www.vinted.co.uk/catalog?search_text=Yeezy%20foam&currency=GBP&order=newest_first&brand_ids[]=115490",1,1)
        items11 = vinted.items.search("https://www.vinted.co.uk/catalog?search_text=Yeezy%20slide&currency=GBP&order=newest_first&brand_ids[]=115490",1,1)
        items12 = vinted.items.search("https://www.vinted.co.uk/catalog?search_text=Yeezy%20boost&currency=GBP&order=newest_first",1,1)

        items13 = vinted.items.search("https://www.vinted.co.uk/catalog?search_text=Airmax&currency=GBP&order=newest_first&brand_ids[]=53",1,1)
        items14 = vinted.items.search("https://www.vinted.co.uk/catalog?search_text=airmax%20tn&currency=GBP&order=newest_first&brand_ids[]=5977",1,1)
        items15 = vinted.items.search("https://www.vinted.co.uk/catalog?search_text=airmax%2095&currency=GBP&order=newest_first&brand_ids[]=5977",1,1)
        items16 = vinted.items.search("https://www.vinted.co.uk/catalog?search_text=corteiz%20air%20max%2095&currency=GBP&order=newest_first&brand_ids[]=5977&brand_ids[]=3036449",1,1)
        items17 = vinted.items.search("https://www.vinted.co.uk/catalog?search_text=air%20max%20patta&currency=GBP&order=newest_first&brand_ids[]=5977&brand_ids[]=6081602",1,1)
        items18 = vinted.items.search("https://www.vinted.co.uk/catalog?search_text=adidas%20gazelle&currency=GBP&order=newest_first&brand_ids[]=252652&brand_ids[]=14",1,1)

        if items and items2 and items3 and items4 and items5 and items6 and items7 and items8 and items9 and items10 and items11 and items12 and items13 and items14 and items15 and items16 and items17 and items18:
            latestItem = items[0]
            latestItem2 = items2[0]
            latestItem3 = items3[0]
            latestItem4 = items4[0]
            latestItem5 = items5[0]
            latestItem6 = items6[0]
            latestItem7 = items7[0]
            latestItem8 = items8[0]
            latestItem9 = items9[0]
            latestItem10 = items10[0]
            latestItem11 = items11[0]
            latestItem12 = items12[0]
            latestItem13 = items13[0]
            latestItem14 = items14[0]
            latestItem15 = items15[0]
            latestItem16 = items16[0]
            latestItem17 = items17[0]
            latestItem18 = items18[0]
        else:
            return

        if val == None:
            print('Monitor live')
            print(latestItem.title)
        elif val != latestItem.url and lastItem != latestItem.title and lastItem2 != latestItem.title and lastItem3 != latestItem.title and lastItem4 != latestItem.title and lastItem5 != latestItem.title and lastItem6 != latestItem.title and lastItem7 != latestItem.title and lastItem8 != latestItem.title and lastItem9 != latestItem.title and lastItem10 != latestItem.title and lastItem11 != latestItem.title and lastItem12 != latestItem.title and lastItem13 != latestItem.title and lastItem14 != latestItem.title and lastItem15 != latestItem.title and lastItem16 != latestItem.title and lastItem17 != latestItem.title and lastItem18 != latestItem.title:
            print(latestItem.title)
            url = "https://canary.discord.com/api/webhooks/1258431841451511809/-A9gALygTkR46PoPfwPPrCBDUXSzfcFyWWqiM62skioVfRaq6n3iNIGwi9qiHuDHxT9Y"
            sendWebhook(latestItem, url)
            lastItem = latestItem.title
        elif val2 != latestItem2.url and lastItem != latestItem2.title and lastItem2 != latestItem2.title and lastItem3 != latestItem2.title and lastItem4 != latestItem2.title and lastItem5 != latestItem2.title and lastItem6 != latestItem2.title and lastItem7 != latestItem2.title and lastItem8 != latestItem2.title and lastItem9 != latestItem2.title and lastItem10 != latestItem2.title and lastItem11 != latestItem2.title and lastItem12 != latestItem2.title and lastItem13 != latestItem2.title and lastItem14 != latestItem2.title and lastItem15 != latestItem2.title and lastItem16 != latestItem2.title and lastItem17 != latestItem2.title and lastItem18 != latestItem2.title:
            print(latestItem2.title)
            url = "https://canary.discord.com/api/webhooks/1261687617183809638/SgKDwqoW5UM1OXlIWNwkav3ClDZr7x5VOBJo13aIArWBxCG-oe_TE7eMIGFBmEoy6YWG"
            sendWebhook(latestItem2, url)   
            lastItem2 = latestItem2.title
        elif val3 != latestItem3.url and lastItem != latestItem3.title and lastItem2 != latestItem3.title and lastItem3 != latestItem3.title and lastItem4 != latestItem3.title and lastItem5 != latestItem3.title and lastItem6 != latestItem3.title and lastItem7 != latestItem3.title and lastItem8 != latestItem3.title and lastItem9 != latestItem3.title and lastItem10 != latestItem3.title and lastItem11 != latestItem3.title and lastItem12 != latestItem3.title and lastItem13 != latestItem3.title and lastItem14 != latestItem3.title and lastItem15 != latestItem3.title and lastItem16 != latestItem3.title and lastItem17 != latestItem3.title and lastItem18 != latestItem3.title:
            print(latestItem3.title)
            url = "https://canary.discord.com/api/webhooks/1261728971029090396/FrJTnNSfdBSwaOwQ3ihZ7iPAiv3i3ammqAscHQ_Ly5p7RME2tRoBj9V7CA0JtT17QUR7"
            sendWebhook(latestItem3, url)   
            lastItem3 = latestItem3.title
        elif val4 != latestItem4.url and lastItem != latestItem4.title and lastItem2 != latestItem4.title and lastItem3 != latestItem4.title and lastItem4 != latestItem4.title and lastItem5 != latestItem4.title and lastItem6 != latestItem4.title and lastItem7 != latestItem4.title and lastItem8 != latestItem4.title and lastItem9 != latestItem4.title and lastItem10 != latestItem4.title and lastItem11 != latestItem4.title and lastItem12 != latestItem4.title and lastItem13 != latestItem4.title and lastItem14 != latestItem4.title and lastItem15 != latestItem4.title and lastItem16 != latestItem4.title and lastItem17 != latestItem4.title and lastItem18 != latestItem4.title:
            print(latestItem4.title)
            url = "https://canary.discord.com/api/webhooks/1261319799208673392/6FmAds8KOnoW_y64sUY9jjhfqp-zjQUnkCwyH6imrvS3Y73SmqYtKgW41Xl38rUHdtxx"
            sendWebhook(latestItem4, url)   
            lastItem4 = latestItem4.title
        elif val5 != latestItem5.url and lastItem != latestItem5.title and lastItem2 != latestItem5.title and lastItem3 != latestItem5.title and lastItem4 != latestItem5.title and lastItem5 != latestItem5.title and lastItem6 != latestItem5.title and lastItem7 != latestItem5.title and lastItem8 != latestItem5.title and lastItem9 != latestItem5.title and lastItem10 != latestItem5.title and lastItem11 != latestItem5.title and lastItem12 != latestItem5.title and lastItem13 != latestItem5.title and lastItem14 != latestItem5.title and lastItem15 != latestItem5.title and lastItem16 != latestItem5.title and lastItem17 != latestItem5.title and lastItem18 != latestItem5.title:
            print(latestItem5.title)
            url = "https://canary.discord.com/api/webhooks/1261693050753650780/rwjq8B-3xzSogh8vczR8RZkmFEc7Owv8WCDHP9LG_OJ2FGUZv_SmSanEpPvBgcVUO7SE"
            sendWebhook(latestItem5, url)   
            lastItem5 = latestItem5.title
        elif val6 != latestItem6.url and lastItem != latestItem6.title and lastItem2 != latestItem6.title and lastItem3 != latestItem6.title and lastItem4 != latestItem6.title and lastItem5 != latestItem6.title and lastItem6 != latestItem6.title and lastItem7 != latestItem6.title and lastItem8 != latestItem6.title and lastItem9 != latestItem6.title and lastItem10 != latestItem6.title and lastItem11 != latestItem6.title and lastItem12 != latestItem6.title and lastItem13 != latestItem6.title and lastItem14 != latestItem6.title and lastItem15 != latestItem6.title and lastItem16 != latestItem6.title and lastItem17 != latestItem6.title and lastItem18 != latestItem6.title:
            print(latestItem6.title)
            url = "https://canary.discord.com/api/webhooks/1261693139702251560/uUttlQmjljLkwPd0IeU3eJUJ1_YvSi9m9_3IfdnLt8Gk97ivvTbMwv4UJr4mZsJJKhTB"
            sendWebhook(latestItem6, url)   
            lastItem6 = latestItem6.title
        if val7 != latestItem7.url and lastItem != latestItem7.title and lastItem2 != latestItem7.title and lastItem3 != latestItem7.title and lastItem4 != latestItem7.title and lastItem5 != latestItem7.title and lastItem6 != latestItem7.title and lastItem7 != latestItem7.title and lastItem8 != latestItem7.title and lastItem9 != latestItem7.title and lastItem10 != latestItem7.title and lastItem11 != latestItem7.title and lastItem12 != latestItem7.title and lastItem13 != latestItem7.title and lastItem14 != latestItem7.title and lastItem15 != latestItem7.title and lastItem16 != latestItem7.title and lastItem17 != latestItem7.title and lastItem18 != latestItem7.title:
            print(latestItem7.title)
            url = "https://canary.discord.com/api/webhooks/1261332801211469845/NSxlGYeNjPT0jjR8AxG3-o9l-qG9NfKOWV-vgFLb_eIU_RnRBdU5rWrEHCW5Pd7CiKuC"
            sendWebhook(latestItem7, url)   
            lastItem7 = latestItem7.title
        elif val8 != latestItem8.url and lastItem != latestItem8.title and lastItem2 != latestItem8.title and lastItem3 != latestItem8.title and lastItem4 != latestItem8.title and lastItem5 != latestItem8.title and lastItem6 != latestItem8.title and lastItem7 != latestItem8.title and lastItem8 != latestItem8.title and lastItem9 != latestItem8.title and lastItem10 != latestItem8.title and lastItem11 != latestItem8.title and lastItem12 != latestItem8.title and lastItem13 != latestItem8.title and lastItem14 != latestItem8.title and lastItem15 != latestItem8.title and lastItem16 != latestItem8.title and lastItem17 != latestItem8.title and lastItem18 != latestItem8.title:
            print(latestItem8.title)
            url = "https://canary.discord.com/api/webhooks/1261697189294374994/HrEcuVlRHoAPpJHBMeNibaUahhV19xcrk7OaWWlGpylEPy__PDskRLgRgDAsGTzf7Gxg"
            sendWebhook(latestItem8, url)   
            lastItem8 = latestItem8.title
        elif val9 != latestItem9.url and lastItem != latestItem9.title and lastItem2 != latestItem9.title and lastItem3 != latestItem9.title and lastItem4 != latestItem9.title and lastItem5 != latestItem9.title and lastItem6 != latestItem9.title and lastItem7 != latestItem9.title and lastItem8 != latestItem9.title and lastItem9 != latestItem9.title and lastItem10 != latestItem9.title and lastItem11 != latestItem9.title and lastItem12 != latestItem9.title and lastItem13 != latestItem9.title and lastItem14 != latestItem9.title and lastItem15 != latestItem9.title and lastItem16 != latestItem9.title and lastItem17 != latestItem9.title and lastItem18 != latestItem9.title:
            print(latestItem9.title)
            url = "https://canary.discord.com/api/webhooks/1261701009642749992/0jyxyX2SF8r_FmnAzXdY3aVRnz92p_jPBuJs_UDupWkbt3gQ6flgyt7cRKfzpFdwV4ES"
            sendWebhook(latestItem9, url)   
            lastItem9 = latestItem9.title
        elif val10 != latestItem10.url and lastItem != latestItem10.title and lastItem2 != latestItem10.title and lastItem3 != latestItem10.title and lastItem4 != latestItem10.title and lastItem5 != latestItem10.title and lastItem6 != latestItem10.title and lastItem7 != latestItem10.title and lastItem8 != latestItem10.title and lastItem9 != latestItem10.title and lastItem10 != latestItem10.title and lastItem11 != latestItem10.title and lastItem12 != latestItem10.title and lastItem13 != latestItem10.title and lastItem14 != latestItem10.title and lastItem15 != latestItem10.title and lastItem16 != latestItem10.title and lastItem17 != latestItem10.title and lastItem18 != latestItem10.title:
            print(latestItem10.title)
            url = "https://canary.discord.com/api/webhooks/1261704436040994857/UswPxZ3JOxRUXCciqFsnSe4PWXDqc5mVHwEjhLa9djXN37nzeUQqT4XcmIyPgFdEeFBX"
            sendWebhook(latestItem10, url)   
            lastItem10 = latestItem10.title
        elif val11 != latestItem11.url and lastItem != latestItem11.title and lastItem2 != latestItem11.title and lastItem3 != latestItem11.title and lastItem4 != latestItem11.title and lastItem5 != latestItem11.title and lastItem6 != latestItem11.title and lastItem7 != latestItem11.title and lastItem8 != latestItem11.title and lastItem9 != latestItem11.title and lastItem10 != latestItem11.title and lastItem11 != latestItem11.title and lastItem12 != latestItem11.title and lastItem13 != latestItem11.title and lastItem14 != latestItem11.title and lastItem15 != latestItem11.title and lastItem16 != latestItem11.title and lastItem17 != latestItem11.title and lastItem18 != latestItem11.title:
            print(latestItem11.title)
            url = "https://canary.discord.com/api/webhooks/1261705402601570324/tX7dv5MLgSRGmNCXrThRPZ9omj_XcICOsGmlF778ePLwKJhgCUlfqNLcFy3dscJ5B8Vp"
            sendWebhook(latestItem11, url)   
            lastItem11 = latestItem11.title
        elif val12 != latestItem12.url and lastItem != latestItem12.title and lastItem2 != latestItem12.title and lastItem3 != latestItem12.title and lastItem4 != latestItem12.title and lastItem5 != latestItem12.title and lastItem6 != latestItem12.title and lastItem7 != latestItem12.title and lastItem8 != latestItem12.title and lastItem9 != latestItem12.title and lastItem10 != latestItem12.title and lastItem11 != latestItem12.title and lastItem12 != latestItem12.title and lastItem13 != latestItem12.title and lastItem14 != latestItem12.title and lastItem15 != latestItem12.title and lastItem16 != latestItem12.title and lastItem17 != latestItem12.title and lastItem18 != latestItem12.title:
            print(latestItem12.title)
            url = "https://canary.discord.com/api/webhooks/1261702414164295760/4XlJk8nNrQ0zQQ2PtT-eLbEVsKQrGu-bD7n_EZ5L7479hDRTz-ZMQXiAU1eb4IsxhGp3"
            sendWebhook(latestItem12, url)   
            lastItem12 = latestItem12.title
        elif val13 != latestItem13.url and lastItem != latestItem13.title and lastItem2 != latestItem13.title and lastItem3 != latestItem13.title and lastItem4 != latestItem13.title and lastItem5 != latestItem13.title and lastItem6 != latestItem13.title and lastItem7 != latestItem13.title and lastItem8 != latestItem13.title and lastItem9 != latestItem13.title and lastItem10 != latestItem13.title and lastItem11 != latestItem13.title and lastItem12 != latestItem13.title and lastItem13 != latestItem13.title and lastItem14 != latestItem13.title and lastItem15 != latestItem13.title and lastItem16 != latestItem13.title and lastItem17 != latestItem13.title and lastItem18 != latestItem13.title:
            print(latestItem13.title)
            url = "https://canary.discord.com/api/webhooks/1261336595890569306/ch-egpTwr35lBMEcZDzbGH3JLtDzeYeYxXZPqnQBRw8FagxoA11MKio_ZIqIsdkB6Wug"
            sendWebhook(latestItem13, url)   
            lastItem13 = latestItem13.title
        elif val14 != latestItem14.url and lastItem != latestItem14.title and lastItem2 != latestItem14.title and lastItem3 != latestItem14.title and lastItem4 != latestItem14.title and lastItem5 != latestItem14.title and lastItem6 != latestItem14.title and lastItem7 != latestItem14.title and lastItem8 != latestItem14.title and lastItem9 != latestItem14.title and lastItem10 != latestItem14.title and lastItem11 != latestItem14.title and lastItem12 != latestItem14.title and lastItem13 != latestItem14.title and lastItem14 != latestItem14.title and lastItem15 != latestItem14.title and lastItem16 != latestItem14.title and lastItem17 != latestItem14.title and lastItem18 != latestItem14.title:
            print(latestItem14.title)
            url = "https://canary.discord.com/api/webhooks/1261715388694007950/ZNIw8Yen801WAv_kQ73krkL2bDmVS9z-TyCWT2A20zmVr084XSHMQLgVFJfA0G-eO_Q2"
            sendWebhook(latestItem14, url)   
            lastItem14 = latestItem14.title
        elif val15 != latestItem15.url and lastItem != latestItem15.title and lastItem2 != latestItem15.title and lastItem3 != latestItem15.title and lastItem4 != latestItem15.title and lastItem5 != latestItem15.title and lastItem6 != latestItem15.title and lastItem7 != latestItem15.title and lastItem8 != latestItem15.title and lastItem9 != latestItem15.title and lastItem10 != latestItem15.title and lastItem11 != latestItem15.title and lastItem12 != latestItem15.title and lastItem13 != latestItem15.title and lastItem14 != latestItem15.title and lastItem15 != latestItem15.title and lastItem16 != latestItem15.title and lastItem17 != latestItem15.title and lastItem18 != latestItem15.title:
            print(latestItem15.title)
            url = "https://canary.discord.com/api/webhooks/1261715482570919957/n7LLI7HeOVp_0Vu0EQTqo-yzSDH3VXg-olQNhcPAiEmmrNiJ5auQHkrSwNYUGbqvgb8S"
            sendWebhook(latestItem15, url)   
            lastItem15 = latestItem15.title
        elif val16 != latestItem16.url and lastItem != latestItem16.title and lastItem2 != latestItem16.title and lastItem3 != latestItem16.title and lastItem4 != latestItem16.title and lastItem5 != latestItem16.title and lastItem6 != latestItem16.title and lastItem7 != latestItem16.title and lastItem8 != latestItem16.title and lastItem9 != latestItem16.title and lastItem10 != latestItem16.title and lastItem11 != latestItem16.title and lastItem12 != latestItem16.title and lastItem13 != latestItem16.title and lastItem14 != latestItem16.title and lastItem15 != latestItem16.title and lastItem16 != latestItem16.title and lastItem17 != latestItem16.title and lastItem18 != latestItem16.title:
            print(latestItem16.title)
            url = "https://canary.discord.com/api/webhooks/1261715695323054130/Q6lzDSxgq2-eBggcGqsYXrtRsygAXaWMwoLRWU95kdfElwLXY4uZ9a7A-Orgs2ABBCyw"
            sendWebhook(latestItem16, url)   
            lastItem16 = latestItem16.title
        elif val17 != latestItem17.url and lastItem != latestItem17.title and lastItem2 != latestItem17.title and lastItem3 != latestItem17.title and lastItem4 != latestItem17.title and lastItem5 != latestItem17.title and lastItem6 != latestItem17.title and lastItem7 != latestItem17.title and lastItem8 != latestItem17.title and lastItem9 != latestItem17.title and lastItem10 != latestItem17.title and lastItem11 != latestItem17.title and lastItem12 != latestItem17.title and lastItem13 != latestItem17.title and lastItem14 != latestItem17.title and lastItem15 != latestItem17.title and lastItem16 != latestItem17.title and lastItem17 != latestItem17.title and lastItem18 != latestItem17.title:
            print(latestItem17.title)
            url = "https://canary.discord.com/api/webhooks/1261715797139521659/rDneTW2CzYyz83k4S0GR1cl9TC84oaEhGdJGXP0ZNNH7C-Q2WLZmUR9VJjZPfst-pWNT"
            sendWebhook(latestItem17, url)   
            lastItem17 = latestItem17.title
        elif val18 != latestItem18.url and lastItem != latestItem18.title and lastItem2 != latestItem18.title and lastItem3 != latestItem18.title and lastItem4 != latestItem18.title and lastItem5 != latestItem18.title and lastItem6 != latestItem18.title and lastItem7 != latestItem18.title and lastItem8 != latestItem18.title and lastItem9 != latestItem18.title and lastItem10 != latestItem18.title and lastItem11 != latestItem18.title and lastItem12 != latestItem18.title and lastItem13 != latestItem18.title and lastItem14 != latestItem18.title and lastItem15 != latestItem18.title and lastItem16 != latestItem18.title and lastItem17 != latestItem18.title and lastItem18 != latestItem18.title:
            print(latestItem18.title)
            url = "https://canary.discord.com/api/webhooks/1261715920871493715/k-hZxpLPsEBxhR2XFrn7KWZeYo4gX-FJw7oJw_22KnbELMttXe75ygwP93g4zuWC-wTS"
            sendWebhook(latestItem18, url)   
            lastItem18 = latestItem18.title

        val = latestItem.url
        val2 = latestItem2.url
        val3 = latestItem3.url
        val4 = latestItem4.url
        val5 = latestItem5.url
        val6 = latestItem6.url
        val7 = latestItem7.url
        val8 = latestItem8.url
        val9 = latestItem9.url
        val10 = latestItem10.url
        val11 = latestItem11.url
        val12 = latestItem12.url
        val13 = latestItem13.url
        val14 = latestItem14.url
        val15 = latestItem15.url
        val16 = latestItem16.url
        val17 = latestItem17.url
        val18 = latestItem18.url
        time.sleep(30)
        
while True:
    main()



'''
https://canary.discord.com/api/webhooks/1258431841451511809/-A9gALygTkR46PoPfwPPrCBDUXSzfcFyWWqiM62skioVfRaq6n3iNIGwi9qiHuDHxT9Y
'''
