"""Manual GitHub Actions two-phase Rubino OTP enrollment."""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from currencytel.rubino_client import RubinoError, request_sms, verify_sms, load_auth, RubinoRPC, resolve_owned_profile


def main():
    action = os.environ.get('RUBINO_ACTION', '').strip()
    phone = os.environ.get('RUBINO_PHONE', '')
    page = os.environ.get('RUBINO_PAGE_ID', '')
    if not phone or not page:
        raise RubinoError('Set RUBINO_PHONE and RUBINO_PAGE_ID GitHub Secrets')
    if action == 'send_code':
        request_sms(phone)
    elif action == 'verify_code':
        verify_sms(phone, os.environ.get('RUBINO_VERIFICATION_CODE', ''))
        print('Page ownership validation:')
        profile_id = resolve_owned_profile(RubinoRPC(load_auth()), page)
        print('Configured Rubino page verified. Posting remains disabled by default.')
    elif action == 'check_session':
        profile_id = resolve_owned_profile(RubinoRPC(load_auth()), page)
        print('Encrypted Rubino session valid; configured page found.')
    else:
        raise RubinoError('Unsupported action')
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except RubinoError as exc:
        print('Rubino: ' + str(exc), file=sys.stderr)
        raise SystemExit(2)
