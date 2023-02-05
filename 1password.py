import argparse
import colorama

from subprocess import Popen, CalledProcessError, PIPE, DEVNULL

from awsume.awsumepy import hookimpl, safe_print
from awsume.awsumepy.lib import profile
from awsume.awsumepy.lib.logger import logger


# we print only N lines of output to minimize ykman stack trace spam
MAX_OUTPUT_LINES = 2


def find_item(config, mfa_serial):
    config = config.get('1password')
    if not config:
        logger.debug('No config subsection')
        return
    elif type(config) != dict:
        logger.debug('Malformed config subsection')
        return
    item = config.get(mfa_serial)
    if not item:
        logger.debug('No vault item specified for this mfa_serial')
    return item


def get_mfa_serial(profiles, target_name):
    mfa_serial = profile.get_mfa_serial(
        profiles, target_name)
    if not mfa_serial:
        logger.debug('No MFA required')
    return mfa_serial


def beautify(stderr):
    msg = stderr.decode().strip('\n')
    if stderr.startsWith('[ERROR]'):
        return msg[28:]  # len('[ERROR] 2023/02/04 16:29:52')
    else:
        return msg


def get_otp(title):
    try:
        op = Popen(['op', 'item', 'get', '--otp', title],
                   stdout=PIPE, stderr=PIPE)
        linecount = 0
        while True:
            msg = op.stderr.readline().decode()
            if msg == '' and op.poll() is not None:
                break
            elif msg != '':
                if linecount < MAX_OUTPUT_LINES:
                    safe_print(beautify(msg), colorama.Fore.CYAN, end='')
                    linecount += 1
                else:
                    logger.debug(msg.strip('\n'))
        if op.returncode != 0:
            return None
        return op.stdout.readline().decode().strip('\n')
    except FileNotFoundError:
        logger.error('Failed: missing `op` command')
        return None


@hookimpl
def pre_get_credentials(config: dict, arguments: argparse.Namespace, profiles: dict):
    mfa_serial = get_mfa_serial(profiles, arguments.target_profile_name)
    if mfa_serial:
        item = find_item(config, mfa_serial)
        if item:
            arguments.mfa_token = get_otp(item)
