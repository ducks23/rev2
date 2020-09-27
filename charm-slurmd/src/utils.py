#!/usr/bin/python3
"""utils.py module for slurmd charm."""
import os
import subprocess
import sys


def lscpu():
    """Return lscpu as a python dictionary."""
    def format_key(lscpu_key):
        key_lower = lscpu_key.lower()
        replace_hyphen = key_lower.replace("-", "_")
        replace_lparen = replace_hyphen.replace("(", "")
        replace_rparen = replace_lparen.replace(")", "")
        return replace_rparen.replace(" ", "_")

    lscpu_out = subprocess.check_output(['lscpu'])
    lscpu_lines = lscpu_out.decode().strip().split("\n")

    return {
        format_key(line.split(":")[0].strip()): line.split(":")[1].strip()
        for line in lscpu_lines
    }


def cpu_info():
    """Return cpu info needed to generate node inventory."""
    ls_cpu = lscpu()

    return {
        'cpus': ls_cpu['cpus'],
        'threads_per_core': ls_cpu['threads_per_core'],
        'cores_per_socket': ls_cpu['cores_per_socket'],
        'sockets_per_board': ls_cpu['sockets'],
    }


def free_m():
    """Return the real memory."""
    real_mem = ""
    try:
        real_mem = subprocess.check_output(
            "free -m | grep -oP '\\d+' | head -n 1",
            shell=True
        )
    except subprocess.CalledProcessError as e:
        print(e)
        sys.exit(-1)

    return real_mem.decode().strip()


def lspci_nvidia():
    """Check for and return the count of nvidia gpus."""
    gpus = 0
    try:
        gpus = int(
            subprocess.check_output(
                "lspci | grep -i nvidia | awk '{print $1}' "
                "| cut -d : -f 1 | sort -u | wc -l",
                shell=True
            ).decode().strip()
        )
    except subprocess.CalledProcessError as e:
        print(e)
        sys.exit(-1)

    for graphics_processing_unit in range(gpus):
        gpu_path = "/dev/nvidia" + str(graphics_processing_unit)
        if not os.path.exists(gpu_path):
            return 0
    return gpus
