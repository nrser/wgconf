import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="nansi",
    version="0.0.1",
    author="NRSER",
    author_email="neil@neilsouza.com",
    description="Nrser ANSIble",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://nrser.com/nansi",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        # "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX",
    ],
    python_requires='>=3.8',
    install_requires=[
        'ansible>=2.9.4,<3',
        'typeguard>=2.9.1,<3',
    ],
)
