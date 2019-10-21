from setuptools import setup, find_packages


if __name__ == "__main__":
    version = {}

    with open("src/nfv/version.py") as fd:
        exec(fd.read(), version)

    setup(
        version=version["__version__"],
        packages=find_packages("src"),
        package_dir={"": "src"},
        scripts=[
            "src/app/nfvctl",
            "src/tools/cleanup-links.py",
            "src/tools/docker-build.py",
            "src/tools/docker-flush.py",
            "src/tools/tell.py",
        ],
    )
