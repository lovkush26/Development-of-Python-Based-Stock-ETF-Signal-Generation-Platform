from setuptools import setup, find_packages

setup(
    name="alphasignal",
    version="2.4.0",
    description="AI-Powered Stock & ETF Signal Generation Platform",
    packages=find_packages(exclude=["tests*", "scripts*", "docker*"]),
    python_requires=">=3.10",
    install_requires=open("requirements.txt").read().splitlines(),
    entry_points={
        "console_scripts": [
            "alphasignal=main:main",
        ]
    },
)
