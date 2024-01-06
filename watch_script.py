from tgtg import TgtgClient
from json import load, dump
import requests
import schedule
import time
import os
import traceback
import json
import maya
import datetime
import pytz
import inspect
import sys
from urllib.parse import quote
import random
import string
import dateutil.parser

def init_from_json(config_json):
    global favorites_only
    try:
        favorites_only = config_json['tgtg']['favorites_only']
    except KeyError:
        favorites_only = False


try:
    filename = inspect.getframeinfo(inspect.currentframe()).filename
    path = os.path.dirname(os.path.abspath(filename))
    # Load credentials from a file
    f = open(os.path.join(path, 'config.json'), mode='r+')
    config = load(f)
    init_from_json(config)
except FileNotFoundError:
    print("No files found for local credentials.")
    exit(1)
except:
    print("Unexpected error")
    print(traceback.format_exc())
    exit(1)

try:
    # Create the tgtg client with my credentials
    tgtg_client = TgtgClient(access_token=config['tgtg']['credentials']['access_token'], refresh_token=config['tgtg']['credentials']['refresh_token'], user_id=config['tgtg']['credentials']['user_id'], cookie=config['tgtg']['credentials']['cookie'])
except KeyError:
    # print(f"Failed to obtain TGTG credentials.\nRun \"python3 {sys.argv[0]} <your_email>\" to generate TGTG credentials.")
    # exit(1)
    try:
        try:
            email = config['tgtg']['email']
        except KeyError:
            email = input("Type your TooGoodToGo email address: ")
        client = TgtgClient(email=email)
        tgtg_creds = client.get_credentials()
        print(tgtg_creds)
        config['tgtg']['credentials'] = tgtg_creds
        f.seek(0)
        json.dump(config, f, indent = 4)
        f.truncate()
        tgtg_client = TgtgClient(access_token=config['tgtg']['credentials']['access_token'], refresh_token=config['tgtg']['credentials']['refresh_token'], user_id=config['tgtg']['credentials']['user_id'], cookie=config['tgtg']['credentials']['cookie'])
    except:
        print(traceback.format_exc())
        exit(1)
except:
    print("Unexpected error")
    print(traceback.format_exc())
    exit(1)
try:
    bot_token = config['telegram']["bot_token"]
    if bot_token == "BOTTOKEN":
        raise KeyError
except KeyError:
    print(f"Failed to obtain Telegram bot token.\n Put it into config.json.")
    exit(1)
except:
    print(traceback.format_exc())
    exit(1)

try:
    bot_chatID = str(config['telegram']["bot_chatID"])
    if bot_chatID == "0":
        # Get chat ID
        pin = ''.join(random.choice(string.digits) for x in range(6))
        print("Please type \"" + pin + "\" to the bot.")
        while bot_chatID == "0":
            response = requests.get('https://api.telegram.org/bot' + bot_token + '/getUpdates?limit=1&offset=-1') 
            # print(response.json())
            if (response.json()['result'][0]['message']['text'] == pin):
                bot_chatID = str(response.json()['result'][0]['message']['chat']['id'])
                print("Your chat id:" + bot_chatID)
                config['telegram']['bot_chatID'] = int(bot_chatID)
                f.seek(0)
                json.dump(config, f, indent = 4)
                f.truncate()
            time.sleep(1)
except KeyError:
    print(f"Failed to obtain Telegram chat ID.")
    exit(1)
except:
    print(traceback.format_exc())
    exit(1)

try:
    f.close()
except:
    print(traceback.format_exc())
    exit(1)

# Init the favourites in stock list as a global variable
tgtg_in_stock = list()



def telegram_bot_sendtext(bot_message, only_to_admin=True):
    """
    Helper function: Send a message with the specified telegram bot.
    It can be specified if both users or only the admin receives the message
    Follow this article to figure out a specific chatID: https://medium.com/@ManHay_Hong/how-to-create-a-telegram-bot-and-send-messages-with-python-4cf314d9fa3e
    """
    send_text = 'https://api.telegram.org/bot' + bot_token + '/sendMessage?chat_id=' + bot_chatID + '&parse_mode=Markdown&disable_web_page_preview=true&text=' + quote(bot_message)
    response = requests.get(send_text)
    return response.json()

def telegram_bot_sendimage(image_url, image_caption=None):
    """
    For sending an image in Telegram, that can also be accompanied by an image caption
    """
    # Prepare the url for an telegram API call to send a photo
    send_text = 'https://api.telegram.org/bot' + bot_token + '/sendPhoto?chat_id=' + bot_chatID + '&photo=' + image_url
    # If the argument gets passed, at a caption to the image
    if image_caption != None:
        send_text += '&parse_mode=Markdown&caption=' + quote(image_caption)
    response = requests.get(send_text)
    return response.json()

def telegram_bot_delete_message(message_id):
    """
    For deleting a Telegram message
    """
    send_text = 'https://api.telegram.org/bot' + bot_token + '/deleteMessage?chat_id=' + bot_chatID + '&message_id=' + str(message_id)
    response = requests.get(send_text)
    return response.json()

def parse_tgtg_api(api_result):
    """
    For fideling out the few important information out of the api response
    """
    result = list()
    # Go through all stores, that are returned with the api
    for store in api_result:
        current_item = dict()
        current_item['id'] = store['item']['item_id']
        current_item['store_name'] = store['store']['store_name']
        current_item['store_address'] = store['store']['store_location']['address']['address_line']
        current_item['items_available'] = store['items_available']
        if current_item['items_available'] == 0:
            result.append(current_item)
            continue
        current_item['description'] = store['item']['description']
        current_item['category_picture'] = store['item']['cover_picture']['current_url']
        current_item['price_including_taxes'] = str(store['item']['item_price']['minor_units'])[:-(store['item']['item_price']['decimals'])] + "." + str(store['item']['item_price']['minor_units'])[-(store['item']['item_price']['decimals']):]+store['item']['item_price']['code']
        current_item['value_including_taxes'] = str(store['item']['item_value']['minor_units'])[:-(store['item']['item_value']['decimals'])] + "." + str(store['item']['item_value']['minor_units'])[-(store['item']['item_value']['decimals']):]+store['item']['item_value']['code']
        try:
            try:
                store_timezone = pytz.timezone(store['store']['store_time_zone'])
            except KeyError:
                store_timezone = None
            localPickupStart = datetime.datetime.strptime(store['pickup_interval']['start'],'%Y-%m-%dT%H:%M:%S%z').replace(tzinfo=datetime.timezone.utc).astimezone(tz=store_timezone)
            localPickupEnd = datetime.datetime.strptime(store['pickup_interval']['end'],'%Y-%m-%dT%H:%M:%S%z').replace(tzinfo=datetime.timezone.utc).astimezone(tz=store_timezone)
            current_item['pickup_start'] = maya.parse(localPickupStart).slang_date("de").capitalize() + " " + localPickupStart.strftime('%H:%M')
            current_item['pickup_end'] = maya.parse(localPickupEnd).slang_date("de").capitalize() + " " + localPickupEnd.strftime('%H:%M')
        except KeyError:
            #print(KeyError)
            current_item['pickup_start'] = None
            current_item['pickup_end'] = None
        try:
            current_item['rating'] = round(store['item']['average_overall_rating']['average_overall_rating'], 2)
        except KeyError:
            current_item['rating'] = None
        result.append(current_item)
    return result

def toogoodtogo():
    """
    Retrieves the data from tgtg API and selects the message to send.
    """

    # Get the global variable of items in stock and favorites_only
    global tgtg_in_stock
    global favorites_only

    # Get all favorite items
    api_response = tgtg_client.get_items(
        favorites_only=favorites_only,
        latitude=config['location']['lat'],
        longitude=config['location']['long'],
        radius=config['location']['range'],
        page_size=300
    )

    #print("####################")
    #print(api_response)
    #print("####################")

    parsed_api = parse_tgtg_api(api_response)

    # Go through all favourite items and compare the stock
    for item in parsed_api:
        try:
            old_stock = [stock['items_available'] for stock in tgtg_in_stock if stock['id'] == item['id']][0]
        except IndexError:
            old_stock = 0
        try:
            item['msg_id'] = [stock['msg_id'] for stock in tgtg_in_stock if stock['id'] == item['id']][0]
        except:
            pass

        new_stock = item['items_available']

        # Check, if the stock has changed. Send a message if so.
        if new_stock != old_stock:
            # Check if the stock was replenished, send an encouraging image message
            if old_stock == 0 and new_stock > 0:
                message = f"🍽 Es gibt {new_stock} neue Überaschungstüte(n) bei [{item['store_name']}](https://share.toogoodtogo.com/item/{item['id']}) in {item['store_address']}\n"\
                f"_{item['description']}_\n"\
                f"💰 *{item['price_including_taxes']}*/{item['value_including_taxes']}\n"
                if 'rating' in item:
                    message += f"⭐️ {item['rating']}/5\n"
                if 'pickup_start' and 'pickup_end' in item:
                    message += f"⏰ {item['pickup_start']} - {item['pickup_end']}\n"
                message += "ℹ️ toogoodtogo.com"
                tg = telegram_bot_sendimage(item['category_picture'], message)
                try: 
                    item['msg_id'] = tg['result']['message_id']
                except:
                    print(json.dumps(tg))
                    print(item['category_picture'])
                    print(message)
                    print(traceback.format_exc())
            elif old_stock > new_stock and new_stock == 0:
                message = f"❌ Ausverkauft! Es gibt keine Überraschungstüte(n) mehr bei [{item['store_name']}](https://share.toogoodtogo.com/item/{item['id']}) in {item['store_address']}\n"
                telegram_bot_sendtext(message)
                # try:
                #     tg = telegram_bot_delete_message([stock['msg_id'] for stock in tgtg_in_stock if stock['id'] == item['id']][0])
                # except:
                #     print(f"Failed to remove message for item id: {item['id']}")
                #     print(traceback.format_exc())
            else:
                # Prepare a generic string, but with the important info
                message = f"🔄 Änderung von {old_stock} auf {new_stock} Überraschungstüte(n) bei [{item['store_name']}](https://share.toogoodtogo.com/item/{item['id']}) in {item['store_address']}\n"
                telegram_bot_sendtext(message)

    # Reset the global information with the newest fetch
    tgtg_in_stock = parsed_api

    # Print out some maintenance info in the terminal
    print(f"TGTG: API run at {time.ctime(time.time())} successful.")
    # for item in parsed_api:
    #     print(f"{item['store_name']}({item['id']}): {item['items_available']}")



def still_alive():
    """
    This function gets called every 24 hours and sends a 'still alive' message to the admin.
    """
    message = f"Current time: {time.ctime(time.time())}. The bot is still running. "
    telegram_bot_sendtext(message)

def refresh():
    """
    Function that gets called via schedule every 1 minute.
    Retrieves the data from services APIs and selects the messages to send.
    """
    try:
        toogoodtogo()
    except:
        print(traceback.format_exc())
        telegram_bot_sendtext("Error occured: \n```" + str(traceback.format_exc()) + "```")

# Use schedule to set up a recurrent checking
schedule.every(1).minutes.do(refresh)
schedule.every(24).hours.do(still_alive)

# Description of the service, that gets send once
telegram_bot_sendtext("The bot script has started successfully. The bot checks every 1 minute, if there is something new at TooGoodToGo. Every 24 hours, the bots sends a \"still alive\" message.")
refresh()
while True:
    # run_pending
    schedule.run_pending()
    time.sleep(1)
