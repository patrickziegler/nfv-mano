#!/usr/bin/env python3
#
# Copyright (C) 2019 Patrick Ziegler
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import argparse
import os

import docker


def docker_build_image(dockerfile, verbose=False):
    """
    Shell equivalent:
    > filename=$(basename -- "$1")
    > docker build -f "$1" -t "${filename%.*}" ./
    """
    if not os.path.exists(dockerfile):
        raise IOError("'%s' does not exist" % dockerfile)
    path, _ = os.path.splitext(dockerfile)
    base = os.path.basename(path)
    dcli = docker.from_env()
    with open(dockerfile, "rb") as fp:
        kwargs = {
            "fileobj": fp,
            "tag": base,
            "pull": True,
            "rm": True,
        }
        image, logs = dcli.images.build(**kwargs)
        if verbose:
            for line in logs:
                print(line)
        return image


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(type=str, dest="dockerfile")
    parser.add_argument("-v", "--verbose", action="store_true", dest="verbose")
    args = parser.parse_args()
    docker_build_image(
        dockerfile=args.dockerfile,
        verbose=args.verbose,
    )
    print("Done")
