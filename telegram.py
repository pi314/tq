import random
import re
import urllib.request
import json

from queue import Queue

from . import config
from . import utils


runrunrun = True
msg_queue = Queue()


def enable():
    token = init_token()
    config.set('telegram', 'token', token)

    chat_id = init_chat_id()
    config.set('telegram', 'chat_id', chat_id)


def telegram_api(*args, **kwargs):
    token = config.get('telegram', 'token')

    retry_count = 0
    while retry_count < 3:
        try:
            res = urllib.request.urlopen(*args, **kwargs)
            return json.loads(res.read().decode('utf-8'))

        except urllib.error.HTTPError as e:
            if 400 <= e.code < 500:
                return json.loads(e.fp.read().decode('utf-8'))
            retry_count += 1

        except urllib.error.URLError as e:
            print('Got urllib.error.URLError, retry_count={}'.format(retry_count))
            print(e.reason)
            retry_count += 1

    return res


def init_bot_id():
    bot_id = config.get('telegram', 'bot_id')

    if bot_id:
        yn = utils.ask('Override existing bot_id? {}'.format(bot_id), 'ny')
        if not yn or yn == 'n':
            return bot_id

    bot_id = None
    print('Input bot_id')
    try:
        while not bot_id:
            bot_id = input('bot_id >>> ').strip()

            if not bot_id.endswith('bot'):
                print('bot_id should ends with "bot"')
                bot_id = None

    except (EOFError, KeyboardInterrupt):
        exit(1)

    return bot_id


def init_token():
    token = config.get('telegram', 'token')

    if token:
        yn = utils.ask('Override existing token? {}'.format(token), 'ny')
        if not yn or yn == 'n':
            return token

    token = None
    print('I have no token yet, please give me one.')
    try:
        while not token:
            token = input('>>> ').strip()

            if token and not re.match(r'^\d+:\w+$', token):
                print('The token format seems incorrect.')
                print('It should be look like xxxxxxxxx:3bd8d2839afbb0ba2c0067578b7b0bc2')
                token = None

    except (EOFError, KeyboardInterrupt):
        exit(1)

    return token


def init_chat_id():
    token = config.get('telegram', 'token')
    chat_id = config.get('telegram', 'chat_id')

    if chat_id:
        yn = utils.ask('Override existing chat_id? {}'.format(chat_id), 'ny')
        if not yn or yn == 'n':
            return chat_id

    code = random.choice('0123456789') + random.choice('abcdefghijkmnopqrstuvwxyz')

    chat_id = None
    print('I dont know to contact you, please send me this secret code on telegram and then press enter.')
    try:
        while not chat_id:
            input('(press enter after you send me "{code}")'.format(code=code))

            print('Detecting...')
            result = telegram_api('https://api.telegram.org/bot{token}/getUpdates'.format(token=token))['result']
            target = list(filter(lambda x: x['message']['text'] == code, result))

            if not target:
                print('It seems not working, could you try again?')

            else:
                t = target[0]['message']
                chat_id = str(t['chat']['id'])
                master_id = t['from']['username']
                master_name = t['from']['first_name'] + ' ' + t['from']['last_name']
                print('Got message from {you}'.format(you=master_id))
                print('Greeting again, {you}!'.format(you=master_name))

    except (EOFError, KeyboardInterrupt):
        exit(1)

    return chat_id


def send_msg(text):
    token = config.get('telegram', 'token')
    chat_id = config.get('telegram', 'chat_id')

    if not token or not chat_id:
        print('token or chat_id is not initialized, abort sending notification')
        return

    headers = {
        'Content-Type': 'application/json; charset=utf-8',
    }
    message = {
        'chat_id': config.get('telegram', 'chat_id'),
        'text': text,
    }
    req = urllib.request.Request(
        'https://api.telegram.org/bot{token}/sendMessage'.format(token=token),
        headers=headers,
        data=json.dumps(message).encode('utf-8'),
    )

    res = telegram_api(req)


def loop_start():
    while runrunrun:
        msg = msg_queue.get()

        if msg is None:
            break

        send_msg(msg)


def loop_stop():
    global runrunrun

    runrunrun = False
    msg_queue.put(None)


def notify_task(task):
    msg_queue.put(str(task))


def notify_msg(text):
    msg_queue.put(text)
