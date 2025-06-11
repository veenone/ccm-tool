"""
Setup script for the Smartcard Management Tool.
"""

from setuptools import setup, find_packages
import os

# Read README for long description
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

# Read requirements
with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="smartcard-management-tool",
    version="1.0.0",
    author="CCM Tool Developer",
    author_email="developer@example.com",
    description="A comprehensive Python tool for managing smartcards through PC/SC readers",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/username/smartcard-management-tool",  # Update with actual repo
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Security :: Cryptography",
        "Topic :: System :: Hardware",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: POSIX :: Linux",
        "Operating System :: MacOS",
    ],
    python_requires=">=3.7",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=6.0",
            "pytest-cov>=2.0",
            "black>=21.0",
            "flake8>=4.0",
            "mypy>=0.900",
        ],
    },
    entry_points={
        "console_scripts": [
            "ccm-tool=ccm_tool:cli",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["config/*.yaml", "examples/*.py"],
    },
    keywords="smartcard pcsc globalplatform security-domain scp02 scp03",
    project_urls={
        "Bug Reports": "https://github.com/username/smartcard-management-tool/issues",
        "Source": "https://github.com/username/smartcard-management-tool",
        "Documentation": "https://github.com/username/smartcard-management-tool/wiki",
    },
)
