# Contributor's Guide

## One-Time Setup

### Virtual Environment

Install `pipenv` and create a venv for development of this package.

```sh
pip3 install pipenv
pipenv install
```

### AWSume Configuration

To test this package, you will need profile(s) in your `~/.awsume/config.yml` that require MFA.

For example, we might have two profiles:
- `alpha`, a login account where we have permanent credentials
- `bravo`, an account that uses ephemeral STS credentials via role assumption
from alpha.

We will test assuming via the chain `alpha -> bravo` where `alpha` will require MFA.
The configuration file would look like:

```
[default]
profile= alpha
region = us-east-2

[profile alpha]
region = us-east-2
mfa_serial = arn:aws:iam::012345678901:mfa/user@example.com

[profile bravo]
region = us-east-2
role_arn = arn:aws:iam::987654321098:role/SomeTargetRole
source_profile=alpha

```

## Test Your Changes

Enter the venv and install your latest changes from local sources.

```sh
pipenv shell
pip3 install .
```

Now you can invoke `awsume` to test your changes.

## Release Your Changes

### Prepare the Release

1. Edit `setup.py` and increment the version number appropriately, following the rules of [semver](https://semver.org/).
2. Commit your changes; tag with `vX.Y.Z`
3. Record the release on GitHub: `git push; git push --tags`

### Publish to PyPI

```sh
# Enter the venv to ensure that we will build the package correctly
pipenv install --dev
pipenv shell

# Inside the venv, run these commands (see Makefile for details)
make clean
make build
make publish
```
