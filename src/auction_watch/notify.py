"""Push notifications through ntfy.sh."""
import urllib.request


def request(topic, title, body, click=None):
    headers = {"Title": title}
    if click:
        headers["Click"] = click
    return f"https://ntfy.sh/{topic}", headers, body.encode()


def push(topic, title, body, click=None):
    url, headers, data = request(topic, title, body, click)
    with urllib.request.urlopen(urllib.request.Request(url, data=data, headers=headers), timeout=20) as r:
        return r.status
