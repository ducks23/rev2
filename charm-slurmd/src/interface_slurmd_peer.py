#!/usr/bin/python3
"""SlurmdPeer."""
import json
import logging
import subprocess


from ops.framework import (
    EventBase,
    EventSource,
    Object,
    ObjectEvents,
)
from utils import cpu_info, free_m, lspci_nvidia


logger = logging.getLogger()


class SlurmdPeerAvailableEvent(EventBase):
    """Emmited on the relation_changed event."""


class PeerRelationEvents(ObjectEvents):
    """Peer Relation Events."""

    slurmd_peer_available = EventSource(SlurmdPeerAvailableEvent)


class SlurmdPeer(Object):
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

        event.relation.data[self.model.unit]['inventory'] = json.loads(
            _get_inventory(
                node_name,
                node_addr
            )
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
            json.loads(relation.data[peer]['inventory'])
            for peer in peers if peer.name in slurmd_peers
        ]

        # Add our hostname and inventory to the slurmd_info
        slurmd_info.append(
            json.loads(relation.data[self.model.unit]['inventory'])
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


def _get_inventory(node_name, node_addr):
    """Assemble and return the node info."""
    mem = free_m()
    processor_info = cpu_info()
    gpus = lspci_nvidia()

    inventory = {
        'node_name': node_name,
        'node_addr': node_addr,
        'state': "UNKNOWN",
        'real_memory': mem,
        **processor_info,
    }

    if (gpus > 0):
        inventory['gres'] = gpus

    return inventory
