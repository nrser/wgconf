import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="wireguard-config",
    version="0.0.1",
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