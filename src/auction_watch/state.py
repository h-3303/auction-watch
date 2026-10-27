"""Watchlist state, encrypted so it can live in a public repo."""
import json

from cryptography.fernet import Fernet


def new_key():
    return Fernet.generate_key().decode()


def seal(obj, key):
    return Fernet(key.encode()).encrypt(json.dumps(obj).encode())


def unseal(blob, key):
    return json.loads(Fernet(key.encode()).decrypt(blob))
