import contextlib
import json
import os
import re
from functools import partial
from typing import Callable

import requests
from flask import Flask, request

SUPPORTED_COMMANDS = [
    'subscribe',
    'unsubscribe',
    'help'
]
SUPPORTED_APPS = [
    'trello',
    'zeplin'
]


def load_user_info(path: str = 'users.json'):
    if not os.path.exists(path):
        return {}
    with open(path, 'r') as in_file:
        return json.loads(in_file.read())


def save_user_info(user_info: dict,
                   path: str = 'users.json'):
    with open(path, 'w') as out_file:
        out_file.write(json.dumps(
            user_info, indent=2, ensure_ascii=False, default=str
        ))


def upsert_user_info(slack_id: str,
                     app: str,
                     app_user_id: str,
                     user_info_path: str = 'users.json'):
    users = load_user_info(user_info_path) or {}
    users[slack_id] = users.get(slack_id) or {}
    users[slack_id][app] = app_user_id
    save_user_info(
        user_info=users,
        path=user_info_path
    )


def remove_user_info(slack_id: str,
                     app: str,
                     user_info_path: str = 'users.json'):
    users = load_user_info(user_info_path) or {}
    users[slack_id] = users.get(slack_id) or {}
    del users[slack_id][app]
    save_user_info(
        user_info=users,
        path=user_info_path
    )


def handle_user_command(sender_id: str,
                        message: str,
                        message_sender: Callable):
    commands = message.split()
    if commands[0].lower() not in SUPPORTED_COMMANDS:
        message_sender(
            message=f'Unsupported command ({commands[0]})'
        )
        message_sender(
            message=f'e.g. subscribe trello hs_lee\n'
                    f'e.g. subscribe zeplin hs_lee\n'
                    f'e.g. unsubscribe trello\n'
                    f'e.g. unsubscribe zeplin'
        )
        raise Exception(f'Unsupported command ({commands[0]})')
    if commands[0].lower() == 'subscribe':
        if commands[1].lower() not in SUPPORTED_APPS:
            message_sender(
                message=f'Unsupported app ({commands[1]})'
            )
            message_sender(
                message=f'e.g. subscribe trello hs_lee\n'
                        f'e.g. subscribe zeplin hs_lee\n'
                        f'e.g. unsubscribe trello\n'
                        f'e.g. unsubscribe zeplin'
            )
            raise Exception(f'Unsupported app ({commands[1]})')
        upsert_user_info(
            slack_id=sender_id,
            app=commands[1],
            app_user_id=commands[2],
        )
        message_sender(
            message=f'Ok. subscribe {commands[2]} for {commands[1]}'
        )
    elif commands[0].lower() == 'unsubscribe':
        if commands[1].lower() not in SUPPORTED_APPS:
            message_sender(
                message=f'Unsupported app ({commands[1]})'
            )
            message_sender(
                message=f'e.g. subscribe trello hs_lee\n'
                        f'e.g. subscribe zeplin hs_lee\n'
                        f'e.g. unsubscribe trello\n'
                        f'e.g. unsubscribe zeplin'
            )
            raise Exception(f'Unsupported app ({commands[1]})')
        remove_user_info(
            slack_id=sender_id,
            app=commands[1]
        )
        message_sender(
            message=f'Unsubscribe {commands[1]}'
        )
    elif commands[0].lower() == 'help':
        message_sender(
            message=f'e.g. subscribe trello hs_lee\n'
                    f'e.g. subscribe zeplin hs_lee\n'
                    f'e.g. unsubscribe trello\n'
                    f'e.g. unsubscribe zeplin'
        )


def send_message(channel: str,
                 message: str,
                 thread_ts: str = None):
    return requests.post(
        url='https://slack.com/api/chat.postMessage',
        headers={
            'Authorization': f'Bearer {os.getenv("SLACK_BOT_TOKEN")}'
        },
        json={
            'channel': channel,
            'text': message,
            **({
                   'thread_ts': thread_ts
               } if thread_ts else {})
        }
    )


def get_app_id_to_slack_id_map(app: str,
                               users: dict):
    return {
        user_info[app]: slack_id
        for slack_id, user_info in users.items()
        if app in user_info
    }


def extract_slack_ids_from_message(text: str,
                                   app_id_to_slack_id_map: dict):
    text_in_parentheses = re.findall(r'\(([^(^)]+)\)', text)
    main_targets = {}
    sub_targets = {}
    for app_id, slack_id in app_id_to_slack_id_map.items():
        position = text.find(f'@{app_id}')
        if position < 0:
            continue
        if f'@{app_id}' not in ''.join(text_in_parentheses):
            if slack_id not in main_targets:
                main_targets[slack_id] = position
        else:
            if slack_id not in sub_targets:
                sub_targets[slack_id] = position
    return {
        'main': [
            slack_id
            for slack_id, _ in sorted(
                main_targets.items(),
                key=lambda item: item[1]
            )
        ],
        'sub': [
            slack_id
            for slack_id, _ in sorted(
                sub_targets.items(),
                key=lambda item: item[1]
            )
        ]
    }


def handle_notification(text: str,
                        channel: str,
                        app_name: str,
                        ts: str):
    id_map = get_app_id_to_slack_id_map(
        app=app_name.lower(),
        users=load_user_info()
    )
    targets = extract_slack_ids_from_message(
        text=text,
        app_id_to_slack_id_map=id_map
    )
    if targets['main']:
        main_targets = ', '.join([
            f'<@{slack_id}>'
            for slack_id in targets['main']
        ])
    else:
        main_targets = ''
    if targets['sub']:
        sub_targets = ', '.join([
            f'<@{slack_id}>'
            for slack_id in targets['sub']
        ])
        sub_targets = f'({sub_targets})'
    else:
        sub_targets = ''

    if main_targets or sub_targets:
        send_message(
            channel=channel,
            message=f'{main_targets} ' + sub_targets,
            thread_ts=ts
        )


def extract_message_info(body: dict):
    event = body['event']
    return {
        'attachments': event.get('attachments'),
        'channel': event['channel'],
        'user_id': event.get('user'),
        'user_name': event.get('user_name'),
        'user_text': event.get('text'),
        'bot_name': (event.get('bot_profile') or {}).get('name'),
        'channel_type': event.get('channel_type'),
        'ts': event.get('thread_ts') or event['ts'],
    }


app = Flask(__name__)


@app.route('/status', methods=['GET'])
def status():
    return 'hello'


@app.route('/incoming', methods=['POST'])
def bot_main():
    if not os.getenv("SLACK_BOT_TOKEN"):
        body = json.loads(request.data.decode('utf-8'))
        return {
            'challenge': body['challenge']
        }
    body = json.loads(request.data.decode('utf-8'))
    message_info = extract_message_info(body)
    if ((message_info['bot_name'] or '').lower() in SUPPORTED_APPS and
            message_info['attachments'] is not None):
        handle_notification(
            text=message_info['attachments'][0].get('text'),
            channel=message_info['channel'],
            app_name=message_info['bot_name'],
            ts=message_info['ts']
        )
        return {}
    if not message_info['bot_name'] and message_info['channel_type'] == 'im':
        with contextlib.suppress(Exception):
            handle_user_command(
                sender_id=message_info['user_id'],
                message=message_info['user_text'],
                message_sender=partial(
                    send_message,
                    channel=message_info['channel'],
                    thread_ts=message_info['ts']
                )
            )

    return {}


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
