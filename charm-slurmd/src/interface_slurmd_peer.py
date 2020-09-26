#!/usr/bin/python3
"""SlurmdPeer."""
import json
import logging
import os
import re
import subprocess
import sys


from ops.framework import (
    EventBase,
    EventSource,
    Object,
    ObjectEvents,
)


logger = logging.getLogger()


class SlurmdPeerAvailableEvent(EventBase):
    """Emmited on the relation_changed event."""


class PeerRelationEvents(ObjectEvents):
    """Peer Relation Events."""

    slurmd_peer_available = EventSource(SlurmdPeerAvailableEvent)


class TestingPeerRelation(Object):
    """TestingPeerRelation."""

    on = PeerRelationEvents()

    def __init__(self, charm, relation_name):
        """Initialize charm attributes."""
        super().__init__(charm, relation_name)
        self._charm = charm
        self._relation_name = relation_name

        self.framework.observe(
            self._charm.on[self._relation_name].relation_created,
            self._on_relation_created
        )

        self.framework.observe(
            self._charm.on[self._relation_name].relation_joined,
            self._on_relation_joined
        )

        self.framework.observe(
            self._charm.on[self._relation_name].relation_changed,
            self._on_relation_changed
        )

        self.framework.observe(
            self._charm.on[self._relation_name].relation_departed,
            self._on_relation_departed
        )

        self.framework.observe(
            self._charm.on[self._relation_name].relation_broken,
            self._on_relation_broken
        )

    def _on_relation_created(self, event):
        """Set hostname and inventory on our unit data."""
        node_name = self._charm.get_hostname()
        node_addr = event.relation.data[self.model.unit]['ingress-address']

        event.relation.data[self.model.unit]['hostname'] = node_name
        event.relation.data[self.model.unit]['inventory'] = get_inventory(
            node_name,
            node_addr
        )
        if self.framework.model.unit.is_leader():
            self.on.slurmd_peer_available.emit()

    def _on_relation_joined(self, event):
        logger.debug("############## LOGGING RELATION JOINED ################")

    def _on_relation_changed(self, event):
        logger.debug("############# LOGGING RELATION CHANGED ################")
        if self.framework.model.unit.is_leader():
            self.on.slurmd_peer_available.emit()

    def _on_relation_departed(self, event):
        logger.debug("############ LOGGING RELATION DEPARTED ################")

    def _on_relation_broken(self, event):
        logger.debug("############ LOGGING RELATION BROKEN ##################")

    def get_slurmd_info(self):
        """Return slurmd inventory."""
        relation = self.framework.model.get_relation(self._relation_name)

        # Comprise slurmd_info with the inventory and hostname of the active
        # slurmd_peers and our own data.
        slurmd_peers = _get_active_peers()
        peers = relation.units

        slurmd_info = [
            {
                'inventory': relation.data[peer]['inventory'],
                'hostname': relation.data[peer]['hostname'],
            }
            for peer in peers if peer.name in slurmd_peers
        ]

        # Add our hostname and inventory to the slurmd_info
        slurmd_info.append(
            {
                'inventory': relation.data[self.model.unit]['inventory'],
                'hostname': relation.data[self.model.unit]['hostname'],
            }
        )
        return slurmd_info


def _related_units(relid):
    """List of related units."""
    units_cmd_line = ['relation-list', '--format=json', '-r', relid]
    return json.loads(
        subprocess.check_output(units_cmd_line).decode('UTF-8')) or []


def _relation_ids(reltype):
    """List of relation_ids."""
    relid_cmd_line = ['relation-ids', '--format=json', reltype]
    return json.loads(
        subprocess.check_output(relid_cmd_line).decode('UTF-8')) or []


def _get_active_peers():
    """Return the active_units."""
    active_units = []
    for rel_id in _relation_ids('slurmd-peer'):
        for unit in _related_units(rel_id):
            active_units.append(unit)
    return active_units


def _get_real_mem():
    """Return the real memory."""
    try:
        real_mem = subprocess.check_output(
            "free -m | grep -oP '\\d+' | head -n 1",
            shell=True
        )
    except subprocess.CalledProcessError as e:
        # logger.debug(e)
        print(e)
        sys.exit(-1)

    return real_mem.decode().strip()


def _get_cpu_info():
    """Return the socket info."""
    try:
        lscpu = \
            subprocess.check_output(
                "lscpu",
                shell=True
            ).decode().replace("(s)", "")
    except subprocess.CalledProcessError as e:
        print(e)
        sys.exit(-1)

    cpu_info = {
        'CPU:': '',
        'Thread per core:': '',
        'Core per socket:': '',
        'Socket:': '',
    }

    try:
        for key in cpu_info:
            cpu_info[key] = re.search(f"{key}.*", lscpu)\
                              .group()\
                              .replace(f"{key}", "")\
                              .replace(" ", "")
    except Exception as error:
        print(f"Unable to set Node configuration: {error}")
        sys.exit(-1)

    return f"CPUs={cpu_info['CPU:']} "\
           f"ThreadsPerCore={cpu_info['Thread per core:']} "\
           f"CoresPerSocket={cpu_info['Core per socket:']} "\
           f"SocketsPerBoard={cpu_info['Socket:']}"


# Get the number of GPUs and check that they exist at /dev/nvidiaX
def _get_gpus():
    gpu = int(
        subprocess.check_output(
            "lspci | grep -i nvidia | awk '{print $1}' "
            "| cut -d : -f 1 | sort -u | wc -l",
            shell=True
        )
    )

    for i in range(gpu):
        gpu_path = "/dev/nvidia" + str(i)
        if not os.path.exists(gpu_path):
            return 0
    return gpu


def get_inventory(node_name, node_addr):
    """Assemble and return the node info."""
    mem = _get_real_mem()
    cpu_info = _get_cpu_info()
    gpus = _get_gpus()

    node_info = f"NodeName={node_name} "\
                f"NodeAddr={node_addr} "\
                f"State=UNKNOWN "\
                f"{cpu_info} "\
                f"RealMemory={mem}"
    if (gpus > 0):
        node_info = f"{node_info} Gres={gpus}"

    return node_info


def get_partition(partition):
    """Return the partition string."""
    nodes = ",".join(partition["hosts"])
    partition_name = partition["name"]

    partition_str = (
        f"PartitionName={partition_name} "
        f"Nodes={nodes} "
        "State=UP "
    )

    if partition.get('config'):
        partition_str += partition['config']

    return partition_str
