# Awsume 1Password Plugin

_Awsume 4+ only_.

This is a plugin that automates the entry of MFA tokens using 1Password.
It replaces AWSume's `MFA Token:` prompt with a biometric unlock and delegates to 1Password for policies on how often unlock is required.
In other words: it saves you from ever having to type an MFA token, ever again!

## Support

If you experience any problems, please [file a bug report](https://github.com/xeger/awsume-1password-plugin/issues/new?assignees=xeger&template=bug_report.md).

## Installation

### Install This Plugin

```
pip3 install awsume-1password-plugin
```

If you've installed awsume with `pipx`, this will install the console plugin in awsume's virtual environment:

```
pipx inject awsume awsume-1password-plugin
```

### Set Up 1Password

1. Install the [1Password CLI](https://developer.1password.com/docs/cli)
2. Enable [biometric unlock](https://developer.1password.com/docs/cli/about-biometric-unlock) of the CLI in 1Password settings

### Configure AWSume

This plugin needs to know which 1Password vault item to use for each MFA token. You can specify this information in your AWSume configuration file.

```yaml
# ~/.awsume/config.yaml

colors: true
1password: AWS (12345, tony)
```

In this example, I have only one MFA token shared among all my accounts (which belong to the same organization).

I have a corresponding 1Password vault item that looks like this:


![Example 1Password Item](docs/screenshots/1p-item.png "Example 1Password Item")


### Multiple MFA Tokens

```yaml
# ~/.awsume/config.yaml

colors: true
fuzzy-match: false
1password:
  "arn:aws:iam::12345:mfa/tony": "AWS (12345, tony)"
  "arn:aws:iam::67890:mfa/tony": "AWS (67890, xeger)"
```

I have two corresponding 1Password vault items for both accounts, with different names to distinguish them.

## Usage

This plugin works automatically in the background; just `awsume` roles as you normally would, and it will invoke the `op` command to obtain TOTP tokens whenever AWSume requires one.

## Troubleshooting

If you experience any trouble, invoke `awsume` with the `--debug` flag and look for log entries that contain `1password`.

The specific command that this plugin invokes is `op item get --otp "Profile Name Here"`; make sure it succeeds when you invoke it manually.

If you can't solve your problem, [create a GitHub issue](https://github.com/xeger/awsume-1password-plugin/issues/new) with diagnostic details and we'll try to help you.
