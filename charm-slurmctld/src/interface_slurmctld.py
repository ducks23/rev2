#!/usr/bin/python3
"""Slurmctld."""
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


class SlurmctldProvidesEvents(ObjectEvents):
    """SlurmctldProvidesEvents."""

    slurm_config_available = EventSource(SlurmConfigAvailableEvent)


class Slurmctld(Object):
    """Slurmctld."""

    on = SlurmctldProvidesEvents()

    def __init__(self, charm, relation_name):
        """Set initial data and observe interface events."""
        super().__init__(charm, relation_name)
        self._charm = charm
        self._relation_name = relation_name

        self.framework.observe(
            self._charm.on[self._relation_name].relation_changed,
            self._on_relation_changed
        )

    def _on_relation_changed(self, event):
        """Obtain and store the munge_key, emit slurm_config_available."""
        event_app_data = event.relation.data.get(event.app)
        if not event_app_data:
            event.defer()
            return
        # Get the munge_key from slurm-configurator
        munge_key = event_app_data.get('munge_key')
        if not munge_key:
            event.defer()
            return
        # Store the munge_key in the main charm state
        self._charm.set_munge_key(munge_key)
        self.on.slurm_config_available.emit()

    @property
    def _relation(self):
        return self.framework.model.get_relation(self._relation_name)

    def set_slurmctld_info_on_app_relation_data(self, slurmctld_info):
        """Set the slurmctld_info to the app data on the relation.

        Setting data on the relation forces the units of related
        slurm-configurator applications to observe the relation-changed
        event so they can acquire and render the updated slurmctld_info.
        """
        relation = self._relation
        if relation:
            relation.data[self.model.app]['slurmctld_info'] = json.dumps(
                slurmctld_info
            )

    def get_slurm_config_from_relation(self):
        """Return slurm_config."""
        relation = self._relation
        if relation:
            app = relation.app
            if app:
                app_data = relation.data.get(app)
                if app_data:
                    if app_data.get('slurm_config'):
                        return json.loads(app_data['slurm_config'])
        return None

    def is_slurm_config_available(self):
        """Return True/False."""
        relation = self._relation
        if relation:
            app = relation.app
            if app:
                app_data = relation.data.get(app)
                if app_data:
                    if app_data.get('slurm_config'):
                        return True
        return False
