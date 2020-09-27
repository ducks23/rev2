#!/usr/bin/python3
"""Slurmd."""
import json

from ops.framework import (
    EventBase,
    EventSource,
    Object,
    ObjectEvents,
)


# logger = logging.getLogger()


class SlurmConfigAvailableEvent(EventBase):
    """Emitted when slurm config is available."""


class SlurmdProvidesEvents(ObjectEvents):
    """SlurmctldProvidesEvents."""

    slurm_config_available = EventSource(SlurmConfigAvailableEvent)


class Slurmd(Object):
    """Slurmd."""

    on = SlurmdProvidesEvents()

    def __init__(self, charm, relation_name):
        """Set initial data and observe interface events."""
        super().__init__(charm, relation_name)
        self._charm = charm
        self._relation_name = relation_name

        self.framework.observe(
            self._charm.on[self._relation_name].relation_changed,
            self._on_relation_changed
        )

        self.framework.observe(
            self._charm.on[self._relation_name].relation_broken,
            self._on_relation_broken
        )

    def _on_relation_changed(self, event):
        event_app_data = event.relation.data.get(event.app)
        if not event_app_data:
            event.defer()
            return

        # Get the munge_key from slurm-configurator
        munge_key = event_app_data.get('munge_key')
        if not munge_key:
            event.defer()
            return
        self._charm.set_munge_key(munge_key)
        self.on.slurm_config_available.emit()

    def _on_relation_broken(self, event):
        self._charm.set_slurm_configurator_available(False)

    @property
    def _relation(self):
        return self.framework.model.get_relation(self._relation_name)

    def set_slurmd_info_on_app_relation_data(self, slurmd_info):
        """Set the slurmd_info on the app relation data.

        Setting data on the application relation forces the units of related
        slurm-configurator application(s) to observe the relation-changed
        event so they can acquire and redistribute the updated slurm config.
        """
        relations = self._charm.framework.model.relations['slurmd']
        for relation in relations:
            relation.data[self.model.app]['slurmd_info'] = json.dumps(
                slurmd_info
            )

    def get_slurm_config_from_relation(self):
        """Return slurm_config."""
        app = self._relation.app
        app_data = self._relation.data[app]
        return json.loads(app_data['slurm_config'])

    def is_slurm_config_available(self):
        """Return True/False."""
        app = self._relation.app
        app_data = self._relation.data[app]
        return app_data['slurm_configurator_available'] == "true"
