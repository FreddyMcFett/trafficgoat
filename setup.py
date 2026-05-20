import re
from pathlib import Path
from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()

with open("requirements.txt", "r", encoding="utf-8") as f:
    requirements = [line.strip() for line in f if line.strip() and not line.startswith("#")]

# Single source of truth: trafficgoat/__init__.py defines __version__.
_init = Path(__file__).parent / "trafficgoat" / "__init__.py"
_match = re.search(r'^__version__\s*=\s*"([^"]+)"', _init.read_text(encoding="utf-8"), re.M)
if not _match:
    raise RuntimeError("Could not locate __version__ in trafficgoat/__init__.py")
_version = _match.group(1)

setup(
    name="trafficgoat",
    version=_version,
    description="Advanced network traffic generator for firewall testing and log generation",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="TrafficGoat Team",
    packages=find_packages(),
    include_package_data=True,
    package_data={
        "trafficgoat": [
            "web/templates/*.html",
            "web/static/css/*.css",
            "web/static/js/*.js",
        ]
    },
    python_requires=">=3.10",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "trafficgoat=trafficgoat.cli:main",
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: POSIX :: Linux",
        "Topic :: System :: Networking",
    ],
)
