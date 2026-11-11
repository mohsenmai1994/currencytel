"""Optional local recovery if Instagram requires interactive verification.

Normal first-time setup is automatic in GitHub Actions with only two Secrets.
This script is not required unless Instagram asks for email/SMS/2FA confirmation.
"""
from __future__ import annotations
import getpass
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from currencytel.publishers.instagram import SESSION_PATH, save_settings


def run() -> int:
    try:
        from instagrapi import Client
        from instagrapi.exceptions import TwoFactorRequired
    except ImportError:
        print('Install requirements-instagram.txt first')
        return 1
    username = input('CurrencyTel Instagram username: ').strip().lstrip('@')
    password = getpass.getpass('Instagram password (hidden): ')
    if not username or not password:
        print('Username and password required')
        return 1
    client = Client()
    def challenge_handler(_name, choice):
        print('Instagram requested confirmation via:', getattr(choice,'name',str(choice)))
        return input('Enter the code (only on your own computer): ').strip()
    client.challenge_code_handler = challenge_handler
    try:
        try:
            success = client.login(username, password)
        except TwoFactorRequired:
            code = input('Enter the two-factor code: ').strip()
            success = client.login(username, password, verification_code=code)
        if not success:
            print('Login was rejected'); return 1
    except Exception as exc:
        print('Login needs attention:', type(exc).__name__)
        return 1
    save_settings(client.get_settings(), username, password, SESSION_PATH)
    print('Encrypted session created at', SESSION_PATH)
    print('Upload only this encrypted file to the identical path in GitHub.')
    print('No INSTAGRAM_SESSION_KEY is required. Keep your username/password only in GitHub Secrets.')
    return 0
if __name__ == '__main__':
    sys.exit(run())
