import setuptools

with open("README.md", "r") as file:
    long_description = file.read()

with open("VERSION", "r") as file:
    version = file.read().strip()

setuptools.setup(
    name="wgconf",
    version=version,
    author="NRSER",
    author_email="neil@nrser.com",
    description="Create and manage WireGuard config files",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://wgconf.nrser.com",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.8',
    install_requires=[
        'typeguard>=2.9.1,<3',
    ],
)