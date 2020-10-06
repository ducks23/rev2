#!/bin/bash

set -e

stage=$1

for charm in slurmctld slurmd slurmdbd slurm-configurator; do
    juju deploy ./$charm.charm --resource slurm=./slurm.resource --series focal
done
