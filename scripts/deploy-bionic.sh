#!/bin/bash

set -e

stage=$1

for charm in slurmctld slurmd slurmdbd slurmconfigurator; do
    juju deploy ./$charm.charm --resource slurm=./slurm.resource --series bionic --bind nat
done
