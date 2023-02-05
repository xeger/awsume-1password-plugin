from setuptools import setup

setup(
    name='awsume-1password-plugin',
    version='1.0.0',
    entry_points={
        'awsume': [
            '1password = 1password'
        ]
    },
    author='Tony Spataro',
    author_email='python@tracker.xeger.net',
    url='https://github.com/xeger/awsume-1password-plugin',
    py_modules=['1password'],
)
