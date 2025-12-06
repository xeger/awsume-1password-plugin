import argparse
import json
import sys
import traceback
from subprocess import PIPE, Popen

import colorama
from awsume.awsumepy import hookimpl, safe_print
from awsume.awsumepy.lib import aws as aws_lib
from awsume.awsumepy.lib import cache as cache_lib
from awsume.awsumepy.lib import profile as profile_lib
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
    mfa_serial = profile_lib.get_mfa_serial(profiles, target_name)
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
        op = Popen(['op', 'item', 'get', '--otp', title], stdout=PIPE, stderr=PIPE)
        linecount = 0
        while True:
            msg = op.stderr.readline().decode()
            if msg == '' and op.poll() is not None:
                break
            elif msg != '' and linecount < MAX_OUTPUT_LINES:
                msg = beautify(msg)
                if msg:
                    safe_print('1Password: ' + msg, colorama.Fore.CYAN)
                    linecount += 1
            else:
                logger.debug(msg.strip('\n'))
        if op.returncode != 0:
            return None
        return op.stdout.readline().decode().strip('\n')
    except FileNotFoundError:
        logger.error('Failed: missing `op` command')
        return None


# Print sad message to console with instructions for filing a bug report.
# Log stack trace to stderr in lieu of safe_print.
def handle_crash():
    safe_print(
        'Error invoking 1Password plugin; please file a bug report:\n  %s'
        % ('https://github.com/xeger/awsume-1password-plugin/issues/new/choose'),
        colorama.Fore.RED,
    )
    traceback.print_exc(file=sys.stderr)


# Execute credential_process and return credentials dict
def run_credential_process(credential_process_cmd):
    try:
        proc = Popen(credential_process_cmd, shell=True, stdout=PIPE, stderr=PIPE)
        stdout, stderr = proc.communicate()
        if proc.returncode != 0:
            logger.error('credential_process failed: %s' % stderr.decode())
            return None
        creds = json.loads(stdout.decode())
        return {
            'AccessKeyId': creds.get('AccessKeyId'),
            'SecretAccessKey': creds.get('SecretAccessKey'),
        }
    except Exception as e:
        logger.error('Failed to run credential_process: %s' % str(e))
        return None


# Handle MFA flow for credential_process profiles. Returns session dict or None.
def handle_credential_process_mfa(first_profile, mfa_serial, otp, force_refresh):
    credential_process = first_profile.get('credential_process')
    source_credentials = run_credential_process(credential_process)
    if not source_credentials:
        return None

    cache_file_name = 'aws-credentials-' + source_credentials['AccessKeyId']
    cache_session = cache_lib.read_aws_cache(cache_file_name)

    if cache_session and cache_lib.valid_cache_session(cache_session) and not force_refresh:
        logger.debug('Using cached MFA session for credential_process profile')
        return cache_session

    try:
        region = first_profile.get('region', 'us-east-1')
        return aws_lib.get_session_token(
            source_credentials,
            region=region,
            mfa_serial=mfa_serial,
            mfa_token=otp,
            ignore_cache=force_refresh,
        )
    except Exception as e:
        logger.error('Failed to get session token: %s' % str(e))
        safe_print('Failed to get MFA session: %s' % str(e), colorama.Fore.RED)
        return None


@hookimpl
def pre_get_credentials(config: dict, arguments: argparse.Namespace, profiles: dict):
    try:
        target_profile_name = profile_lib.get_profile_name(
            config, profiles, arguments.target_profile_name
        )
        if not profiles.get(target_profile_name):
            logger.debug('No profile %s found, skip plugin flow' % target_profile_name)
            return None
        if target_profile_name != None:
            if target_profile_name == "default":
                first_profile_name = "default"
            else:
                role_chain = profile_lib.get_role_chain(
                    config, arguments, profiles, target_profile_name
                )
                first_profile_name = role_chain[0]
            first_profile = profiles.get(first_profile_name)
            # Handle credential_process profiles with MFA by getting session token
            if first_profile.get('credential_process'):
                logger.debug(
                    'Profile %s uses credential_process, handling MFA flow'
                    % first_profile_name
                )
                mfa_serial = profile_lib.get_mfa_serial(profiles, first_profile_name)
                if mfa_serial and not arguments.mfa_token:
                    item = find_item(config, mfa_serial)
                    if item:
                        otp = get_otp(item)
                        if otp:
                            safe_print(
                                'Obtained MFA token from 1Password item: %s' % item,
                                colorama.Fore.CYAN,
                            )
                            session = handle_credential_process_mfa(
                                first_profile, mfa_serial, otp, arguments.force_refresh
                            )
                            if session:
                                safe_print(
                                    'Obtained MFA session credentials',
                                    colorama.Fore.CYAN,
                                )
                                # Replace credential_process with session credentials
                                del profiles[first_profile_name]['credential_process']
                                # Remove mfa_serial since we've already handled MFA
                                if 'mfa_serial' in profiles[first_profile_name]:
                                    del profiles[first_profile_name]['mfa_serial']
                                profiles[first_profile_name]['aws_access_key_id'] = session.get('AccessKeyId')
                                profiles[first_profile_name]['aws_secret_access_key'] = session.get('SecretAccessKey')
                                if session.get('SessionToken'):
                                    profiles[first_profile_name]['aws_session_token'] = session.get('SessionToken')
                return None
            source_credentials = profile_lib.profile_to_credentials(first_profile)
            source_access_key_id = source_credentials.get('AccessKeyId')
            if source_access_key_id == None:
                logger.debug(
                    'No access key for profile %s, skip plugin flow'
                    % first_profile_name
                )
                return None
            cache_file_name = 'aws-credentials-' + source_access_key_id
            cache_session = cache_lib.read_aws_cache(cache_file_name)
            valid_cache_session = cache_session and cache_lib.valid_cache_session(
                cache_session
            )

            mfa_serial = profile_lib.get_mfa_serial(profiles, first_profile_name)
            if (
                mfa_serial
                and (not valid_cache_session or arguments.force_refresh)
                and not arguments.mfa_token
            ):
                item = find_item(config, mfa_serial)
                if item:
                    arguments.mfa_token = get_otp(item)
                    if arguments.mfa_token:
                        safe_print(
                            'Obtained MFA token from 1Password item: %s' % (item),
                            colorama.Fore.CYAN,
                        )
    except Exception:
        handle_crash()
