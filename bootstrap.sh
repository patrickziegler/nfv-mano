#!/bin/bash

set -x

PYTHON="python3"
PROJ_DIR=$(readlink -f "$0" | xargs dirname)
VIRT_ENV="${PROJ_DIR}/.venv"

function mk_venv {
    cd "${PROJ_DIR}"
    # eval $PYTHON -m virtualenv "${VIRT_ENV}" --system-site-packages
    eval $PYTHON -m virtualenv "${VIRT_ENV}"
    source "${VIRT_ENV}/bin/activate"
}

function get_mininet {
    CLONE_DIR="${PROJ_DIR}/extern/mininet"
    git clone --depth 1 https://github.com/mininet/mininet.git "${CLONE_DIR}"
    cd "${CLONE_DIR}"
    make mnexec
    mv -v mnexec "${VIRT_ENV}/bin"
    eval $PYTHON setup.py develop
}

function install_project_dev {
    cd "${PROJ_DIR}"
    eval $PYTHON -m pip install -r "${PROJ_DIR}/requirements.txt"
    eval $PYTHON setup.py develop
}

mk_venv
get_mininet
install_project_dev

function get_linux {
    CLONE_DIR="${PROJ_DIR}/extern/linux"
    git clone --depth 1 https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git "${CLONE_DIR}"
    cd "${CLONE_DIR}"
    make defconfig
    make -j4  # this may safely be interrupted after some seconds
    cd "${CLONE_DIR}/tools/lib/bpf"
    make -j4
}

function get_bpf_next {
    CLONE_DIR="${PROJ_DIR}/extern/bpf-next"
    git clone --depth 1 https://git.kernel.org/pub/scm/linux/kernel/git/bpf/bpf-next.git "${CLONE_DIR}"
    cd "${CLONE_DIR}"
    make defconfig
    make -j4  # this may safely be interrupted after some seconds
    cd "${CLONE_DIR}/tools/lib/bpf"
    make -j4
}

get_linux
