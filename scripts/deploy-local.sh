#!/bin/bash

set -e

stage=$1

for charm in slurmctld slurmd slurmdbd slurm-configurator slurmrestd; do
    juju deploy ./$charm.charm --resource slurm=./slurm.resource --series focal
done
juju deploy mysql
juju relate slurmdbd mysql
juju relate slurmctld slurm-configurator
juju relate slurmd slurm-configurator
juju relate slurmrestd slurm-configurator
juju relate slurmdbd slurm-configurator

