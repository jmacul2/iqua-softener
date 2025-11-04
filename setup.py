from setuptools import setup, find_packages


setup(
    name="iqua_softener",
    version="2.0.0",
    license="MIT",
    author="Artur Zabroński",
    author_email="artur.zabronski@gmail.com",
    maintainer="Jay McEntire",
    maintainer_email="jay.mcentire@usu.edu",
    packages=find_packages(),
    url="https://github.com/arturzx/iqua-softener",
    keywords="iqua softener iqua_softener water treatment",
    description="Python library for controlling iQua water softeners",
    long_description=(
        "A Python library for interacting with iQua water softeners through their API. "
        "Supports reading device data, controlling water shutoff valves, and managing regeneration cycles."
    ),
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Home Automation",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    python_requires=">=3.7",
    install_requires=[
        "requests",
        "PyJWT",
        "websockets",
    ],
    extras_require={
        "dev": ["pytest", "black", "flake8"],
    },
)
