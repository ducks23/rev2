#!/usr/bin/python3
"""Slurmd."""
import json
import logging


from ops.framework import (
    EventBase,
    EventSource,
    Object,
    ObjectEvents,
    StoredState,
)
from ops.model import BlockedStatus


logger = logging.getLogger()


class SlurmdUnAvailableEvent(EventBase):
    """Emmited when the slurmd relation is broken."""


class SlurmdDepartedEvent(EventBase):
    """Emmited when a slurmd unit departs."""


class SlurmdAvailableEvent(EventBase):
    """Emmited when slurmd is available."""


class SlurmdRequiresEvents(ObjectEvents):
    """SlurmClusterProviderRelationEvents."""

    slurmd_available = EventSource(SlurmdAvailableEvent)
    slurmd_departed = EventSource(SlurmdDepartedEvent)
    slurmd_unavailable = EventSource(SlurmdUnAvailableEvent)


class Slurmd(Object):
    """Slurmd."""

    on = SlurmdRequiresEvents()
    _state = StoredState()

    def __init__(self, charm, relation_name):
        """Set self._relation_name and self.charm."""
        super().__init__(charm, relation_name)
        self._charm = charm
        self._relation_name = relation_name

        self.framework.observe(
            self._charm.on[self._relation_name].relation_created,
            self._on_relation_created
        )
        self.framework.observe(
            self._charm.on[self._relation_name].relation_changed,
            self._on_relation_changed
        )
        self.framework.observe(
            self._charm.on[self._relation_name].relation_broken,
            self._on_relation_broken
        )
        self.framework.observe(
            self._charm.on[self._relation_name].relation_departed,
            self._on_relation_departed
        )

    def _on_relation_created(self, event):
        # Check that slurm has been installed so that we know the munge key is
        # available. Defer if slurm has not been installed yet.
        if not self._charm.is_slurm_installed():
            event.defer()
            return
        # Get the munge_key from the slurm_ops_manager and set it to the app
        # data on the relation to be retrieved on the other side by slurmdbd.
        munge_key = self._charm.get_munge_key()
        app_relation_data = event.relation.data[self.model.app]

        app_relation_data['munge_key'] = munge_key
        app_relation_data['slurm_configurator_available'] = "false"

    def _on_relation_changed(self, event):
        """Check for slurmdbd and slurmd, write config, set relation data."""
        if len(self.framework.model.relations['slurmd']) > 0:
            if not self._charm.is_slurmd_available():
                self._charm.set_slurmd_available(True)
            self.on.slurmd_available.emit()
        else:
            self._charm.unit.status = BlockedStatus("Need > 0 units of slurmd")
            event.defer()
            return

    def get_slurmd_node_info(self):
        """Return the node info for units of applications on the relation."""
        nodes_info = list()
        relations = self.framework.model.relations['slurmd']

        for relation in relations:
            app_data = relation.data[relation.app]
            nodes_info.append(json.loads(app_data['slurmd_info']))
        return nodes_info

    def set_slurm_config_on_app_relation_data(
        self,
        relation,
        slurm_config,
    ):
        """Set the slurm_conifg to the app data on the relation.

        Setting data on the relation forces the units of related applications
        to observe the relation-changed event so they can acquire and
        render the updated slurm_config.
        """
        relations = self._charm.framework.model.relations[relation]
        for relation in relations:
            app_relation_data = relation.data[self.model.app]
            app_relation_data['slurm_config'] = json.dumps(slurm_config)
            app_relation_data['slurm_configurator_available'] = "true"
