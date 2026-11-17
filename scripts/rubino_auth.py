"""Manual GitHub Actions two-phase Rubino OTP enrollment.

Runs the third-party login client in a bounded subprocess. GitHub Actions can
otherwise sit silently if a networking call in rulog never returns.
No secret, OTP, phone number or response body is printed by this wrapper.
"""
from __future__ import annotations

import faulthandler
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from currencytel.rubino_client import (
    RubinoError,
    request_sms,
    verify_sms,
    load_auth,
    RubinoRPC,
    resolve_owned_profile,
)

_CHILD_FLAG = '_CT_RUBINO_AUTH_INNER'
_ACTION_LIMITS = {'send_code': 75, 'verify_code': 110, 'check_session': 55}


def main() -> int:
    action = os.environ.get('RUBINO_ACTION', '').strip()
    phone = os.environ.get('RUBINO_PHONE', '')
    page = os.environ.get('RUBINO_PAGE_ID', '')
    if not phone or not page:
        raise RubinoError('Set RUBINO_PHONE and RUBINO_PAGE_ID GitHub Secrets')

    if action == 'send_code':
        print('Rubino SMS: bounded discovery and single SMS request...', flush=True)
        request_sms(phone)
    elif action == 'verify_code':
        print('Rubino OTP: loading challenge and verifying received code...', flush=True)
        verify_sms(phone, os.environ.get('RUBINO_VERIFICATION_CODE', ''))
        print('Rubino OTP: validating ownership of configured page...', flush=True)
        resolve_owned_profile(RubinoRPC(load_auth()), page)
        print('Configured Rubino page verified. Posting remains disabled by default.', flush=True)
    elif action == 'check_session':
        print('Rubino: checking encrypted session and page ownership...', flush=True)
        resolve_owned_profile(RubinoRPC(load_auth()), page)
        print('Encrypted Rubino session valid; configured page found.', flush=True)
    else:
        raise RubinoError('Unsupported action')
    return 0


def _run_guarded() -> int:
    """Avoid indefinite waits in unmaintained/third-party login libraries."""
    action = os.environ.get('RUBINO_ACTION', '').strip()
    if action not in _ACTION_LIMITS:
        print('Rubino: Unsupported action', file=sys.stderr, flush=True)
        return 2

    if os.environ.get(_CHILD_FLAG) == '1':
        # Stack frames only, no local variables or credentials; helps locate hangs.
        faulthandler.enable()
        faulthandler.dump_traceback_later(45, repeat=False)
        try:
            try:
                return main()
            except RubinoError as exc:
                print('Rubino: ' + str(exc), file=sys.stderr, flush=True)
                return 2
        finally:
            faulthandler.cancel_dump_traceback_later()

    env = os.environ.copy()
    env[_CHILD_FLAG] = '1'
    env['PYTHONUNBUFFERED'] = '1'
    max_seconds = _ACTION_LIMITS[action]
    print(f'Rubino: starting {action}; hard timeout {max_seconds}s.', flush=True)
    try:
        completed = subprocess.run(
            [sys.executable, '-u', str(Path(__file__).resolve())],
            env=env,
            timeout=max_seconds,
            check=False,
        )
        return completed.returncode
    except subprocess.TimeoutExpired:
        print(
            'Rubino: login library timed out before confirmation. '
            'The SMS might or might not have been sent; do not repeatedly '
            'run send_code. Check the phone and the diagnostic stack in this log.',
            file=sys.stderr,
            flush=True,
        )
        return 124


if __name__ == '__main__':
    raise SystemExit(_run_guarded())
