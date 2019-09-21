from setuptools import setup, find_packages

import os
import sys
import platform

if platform.uname()[4].startswith("arm") and sys.version.startswith("2"):
    install_requires=['pyserial', 'tqdm', 'numpy']
else:
    install_requires=['pyserial', 'opencv-python-headless', 'tqdm', 'numpy']

__packagename__ = "flirpy"

setup(
    name=__packagename__,
    version='0.0.1',
    packages=find_packages(),
    author='Josh Veitch-Michaelis',
    author_email='j.veitchmichaelis@gmail.com',
    license='MIT',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    zip_safe=False,
    include_package_data=True,
    scripts=['scripts/split_seqs'],
    install_requires = install_requires
)