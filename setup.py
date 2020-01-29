from setuptools import setup, find_packages

import os
import sys
import platform

# Opencv headless not available on ARM platforms, need to manual install
if platform.machine() in ["arm", "aarch64", "aarch64_be", "armv8b", "armv8l"]:
    install_requires=['pyserial', 'tqdm', 'numpy']

    print("System detected as ARM. This library depends on OpenCV, which is not \
           available as a wheel yet so you will need to build from scratch. If you're running \
           aarch64, you can try 'pip install opencv-python-aarch64' but this is not officially supported.")
else:
    install_requires=['pyserial', 'opencv-python-headless', 'tqdm', 'numpy', 'pyudev', 'psutil']

__packagename__ = "flirpy"

setup(
    name=__packagename__,
    version='0.0.7',
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
