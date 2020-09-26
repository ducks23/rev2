#!/usr/bin/python3
"""Elasticserch interface."""
import logging

from ops.framework import (
    EventBase,
    EventSource,
    Object,
    ObjectEvents,
)

logger = logging.getLogger()


class ElasticsearchAvailableEvent(EventBase):
    """ElasticsearchAvailable event."""


class ElasticsearchUnAvailableEvent(EventBase):
    """ElasticsearchUnAvailable event."""


class ElasticsearchEvents(ObjectEvents):
    """ElasticsearchEvents."""

    elasticsearch_available = EventSource(ElasticsearchAvailableEvent)
    elasticsearch_unavailable = EventSource(ElasticsearchUnAvailableEvent)


class Elasticsearch(Object):
    """Elasticsearch interface."""

    on = ElasticsearchEvents()

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
        """Set elasticsearch_ingress to _stored."""
        ingress = event.relation.data[event.unit]['ingress-address']
        self.charm.set_elasticsearch_ingress(f'http://{ingress}:9200')
        self.on.elasticsearch_available.emit()

    def _on_relation_broken(self, event):
        """Set elasticsearch_ingress and emit elasticsearch_unavailable."""
        self.charm.set_elasticsearch_ingress("")
        self.on.elasticsearch_unavailable.emit()
