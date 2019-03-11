from setuptools import setup, find_packages

import os

__packagename__ = "flirpy"

setup(
    name=__packagename__,
    version='0.0.1',
    packages=find_packages(),
    author='Josh Veitch-Michaelis',
    author_email='j.veitchmichaelis@gmail.com',
    license='MIT',
    long_description=open('README.md').read(),
    zip_safe=False,
    include_package_data=True,
    scripts=['scripts/split_seqs'],
    install_requires=['pyserial', 'opencv-python-headless', 'tqdm', 'numpy']
)