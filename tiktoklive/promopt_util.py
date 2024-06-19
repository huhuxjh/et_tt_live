def chat_with(who: str, content: str):
    base = f'{who} says {content}, reply it'
    return base


def welcome_with(who: str):
    base = f'{who} come in, greet {who}'
    return base


def liked_with(who: str):
    base = f'{who} liked the live stream, thanks to {who}'
    return base


def followed_with(who: str):
    base = f'{who} subscribed the live stream, thanks to {who}'
    return base


def shared_with(who: str):
    base = f'{who} shared the live stream, thanks to {who}'
    return base