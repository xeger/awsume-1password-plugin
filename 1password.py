import argparse
import colorama
import traceback
import sys

from subprocess import Popen, PIPE

from awsume.awsumepy import hookimpl, safe_print
from awsume.awsumepy.lib import profile
from awsume.awsumepy.lib.logger import logger


# Truncate proxied subprocess output to avoid stack trace spam
MAX_OUTPUT_LINES = 2


# Map an MFA serial to a 1Password vault item
def find_item(config, mfa_serial):
    config = config.get('1password')
    item = None
    if not config:
        logger.debug('No config subsection')
    elif type(config) == str:
        item = config
    elif type(config) == dict:
        item = config.get(mfa_serial)
    else:
        logger.debug('Malformed config subsection')
        return
    if not item:
        logger.debug('No vault item specified for this mfa_serial')
    return item


# Find the MFA serial for a given AWS profile.
def get_mfa_serial(profiles, target_name):
    mfa_serial = profile.get_mfa_serial(
        profiles, target_name)
    if not mfa_serial:
        logger.debug('No MFA required')
    return mfa_serial


# Make a 1Password error message more succinct before safe_printing it.
# Return None if it's not worth printing (e.g. an expected error).
def beautify(msg):
    if msg.startswith('[ERROR]'):
        return msg[28:]  # len('[ERROR] 2023/02/04 16:29:52')
    elif msg.startswith('error initializing client:'):
        return msg[26:]  # len('error initializing client:')
    else:
        return msg


# Call 1Password to get an OTP for a given vault item.
def get_otp(title):
    try:
        op = Popen(['op', 'item', 'get', '--otp', title],
                   stdout=PIPE, stderr=PIPE)
        linecount = 0
        while True:
            msg = op.stderr.readline().decode()
            if msg == '' and op.poll() is not None:
                break
            elif msg != '' and linecount < MAX_OUTPUT_LINES:
                msg = beautify(msg)
                if msg:
                    safe_print('1Password: ' + msg,
                               colorama.Fore.CYAN)
                    linecount += 1
            else:
                logger.debug(msg.strip('\n'))
        if op.returncode != 0:
            return None
        return op.stdout.readline().decode().strip('\n')
    except FileNotFoundError:
        logger.error('Failed: missing `op` command')
        return None


# Find canonical profile name (e.g. with fuzzy matching rules).
def canonicalize(config, profiles, name):
    target_name = profile.get_profile_name(config, profiles, name, log=False)
    if profiles.get(target_name) != None:
        return target_name
    else:
        return None


# Print sad message to console with instructions for filing a bug report.
# Log stack trace to stderr in lieu of safe_print.
def handle_crash():
    safe_print('Error invoking 1Password plugin; please file a bug report:\n  %s' %
               ('https://github.com/xeger/awsume-1password-plugin/issues/new/choose'), colorama.Fore.RED)
    traceback.print_exc(file=sys.stderr)


@hookimpl
def pre_get_credentials(config: dict, arguments: argparse.Namespace, profiles: dict):
    try:
        target_profile_name = canonicalize(
            config, profiles, arguments.target_profile_name)
        if target_profile_name != None:
            mfa_serial = get_mfa_serial(profiles, target_profile_name)
            if mfa_serial and not arguments.mfa_token:
                item = find_item(config, mfa_serial)
                if item:
                    arguments.mfa_token = get_otp(item)
                    if arguments.mfa_token:
                        safe_print('Obtained MFA token from 1Password item: %s' %
                                   (item), colorama.Fore.CYAN)
    except Exception:
        handle_crash()
