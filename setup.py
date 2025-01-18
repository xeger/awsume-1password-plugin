from setuptools import setup

setup(
    name='awsume-1password-plugin',
    version='1.2.4',
    description='Automates awsume MFA entry via 1Password CLI.',
    entry_points={'awsume': ['1password = 1password']},
    author='Tony Spataro',
    author_email='pypi@tracker.xeger.net',
    url='https://github.com/xeger/awsume-1password-plugin',
    py_modules=['1password'],
)
