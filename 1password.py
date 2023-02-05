import argparse
import re

from subprocess import run, CalledProcessError, PIPE, DEVNULL

from awsume.awsumepy import hookimpl, safe_print
from awsume.awsumepy.lib import profile
from awsume.awsumepy.lib.logger import logger


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


def describe_failure(stderr):
    # [ERROR] 2023/02/04 16:29:52 => 28 characters
    return stderr.decode().strip('\n')[28:]


def get_otp(title):
    try:
        op = run(['op', 'item', 'get', '--otp', title],
                 check=True, stdout=PIPE, stderr=PIPE)
        return op.stdout.decode().strip('\n')
    except CalledProcessError as e:
        logger.error('Failed: `op` command -> %s' %
                     (describe_failure(e.stderr)))
        return None
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
