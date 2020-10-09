#!/bin/bash

set -e

stage=$1

for charm in slurmrestd slurmctld slurmd slurmdbd slurm-configurator; do
	juju deploy ./$charm.charm --resource slurm=./slurm.resource --series bionic --bind nat
done
