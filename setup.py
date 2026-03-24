from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()

with open("requirements.txt", "r", encoding="utf-8") as f:
    requirements = [line.strip() for line in f if line.strip() and not line.startswith("#")]

setup(
    name="trafficgoat",
    version="1.0.0",
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
