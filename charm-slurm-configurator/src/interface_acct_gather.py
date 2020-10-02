#!/usr/bin/python3
"""AcctGather (Influxdb) interface."""
import logging

from ops.framework import (
    EventBase,
    EventSource,
    Object,
    ObjectEvents,
)

logger = logging.getLogger()


class InfluxDBAvailableEvent(EventBase):
    """InfluxDBAvailable event."""


class InfluxDBUnAvailableEvent(EventBase):
    """InfluxDBUnAvailable event."""


class InfluxDBEvents(ObjectEvents):
    """InfluxDBEvents."""

    influxdb_available = EventSource(InfluxDBAvailableEvent)
    influxdb_unavailable = EventSource(InfluxDBUnAvailableEvent)


class InfluxDB(Object):
    """InfluxDB interface."""

    on = InfluxDBEvents()

    def __init__(self, charm, relation_name):
        """Observe relation events."""
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
        """Store influxdb_ingress in the charm."""
        ingress = event.relation.data[event.unit]['ingress-address']
        self.charm.set_influxdb_ingress(ingress)
        self.on.influxdb_available.emit()

    def _on_relation_broken(self, event):
        """Set influxdb_ingress and emit influxdb_unavailable."""
        self.charm.set_influxdb_ingress("")
        self.on.influxdb_unavailable.emit()
