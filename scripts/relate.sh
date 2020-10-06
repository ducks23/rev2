#!/bin/bash

set -e

stage=$1

juju deploy mysql
juju relate slurmdbd mysql
juju relate slurmctld slurm-configurator
juju relate slurmd slurm-configurator
juju relate slurmdbd slurm-configurator
