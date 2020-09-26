#!/usr/bin/python3
"""SlurmctldCharm."""
import logging

from interface_elasticsearch import Elasticsearch
from interface_nhc import Nhc
from interface_slurmctld import Slurmctld
from interface_slurmd import Slurmd
from interface_slurmdbd import Slurmdbd
from interface_slurmrestd import Slurmrestd
from ops.charm import CharmBase
from ops.framework import StoredState
from ops.main import main
from ops.model import (
    ActiveStatus,
    BlockedStatus,
)
from slurm_ops_manager import SlurmManager


logger = logging.getLogger()


class SlurmConfiguratorCharm(CharmBase):
    """Facilitate slurm configuration operations."""

    _stored = StoredState()

    def __init__(self, *args):
        """Init charm, _stored defaults, interfaces and observe events."""
        super().__init__(*args)

        self._stored.set_default(
            elasticsearch_ingress=None,
            munge_key=str(),
            nhc_info=dict(),
            slurm_installed=False,
            slurmctld_available=False,
            slurmd_available=False,
            slurmdbd_available=False,
            slurmrestd_available=False,
        )

        self._slurm_manager = SlurmManager(self, "slurmd")

        self._elasticsearch = Elasticsearch(self, "elasticsearch")
        self._nhc = Nhc(self, "nhc")

        self._slurmd = Slurmd(self, "slurmd")
        self._slurmctld = Slurmctld(self, "slurmctld")
        self._slurmdbd = Slurmdbd(self, "slurmdbd")
        self._slurmrestd = Slurmrestd(self, "slurmrestd")

        ##### Charm lifecycle events #####
        event_handler_bindings = {
            ##### Juju lifecycle events #####
            self.on.install: self._on_install,

            self.on.start:
            self._on_check_status_and_write_config,

            self.on.config_changed:
            self._on_check_status_and_write_config,

            self.on.upgrade_charm: self._on_upgrade,

            ##### User defined charm lifecycle events #####
            self._slurmctld.on.slurmctld_available:
            self._on_check_status_and_write_config,

            self._slurmctld.on.slurmctld_unavailable:
            self._on_check_status_and_write_config,

            self._slurmdbd.on.slurmdbd_available:
            self._on_check_status_and_write_config,

            self._slurmdbd.on.slurmdbd_unavailable:
            self._on_check_status_and_write_config,

            self._slurmd.on.slurmd_available:
            self._on_check_status_and_write_config,

            self._slurmd.on.slurmd_departed:
            self._on_check_status_and_write_config,

            self._slurmd.on.slurmd_unavailable:
            self._on_check_status_and_write_config,

            self._slurmrestd.on.slurmrestd_available:
            self._on_provide_slurmrestd,

            self._elasticsearch.on.elasticsearch_available:
            self._on_check_status_and_write_config,

            self._elasticsearch.on.elasticsearch_unavailable:
            self._on_check_status_and_write_config,

            self._nhc.on.nhc_bin_available:
            self._on_check_status_and_write_config,
        }
        for event, handler in event_handler_bindings.items():
            self.framework.observe(event, handler)

    def _on_install(self, event):
        """Install the slurm snap and set the munge key."""
        # Install the slurm snap and set the snap mode
        self._slurm_manager.install()
        self._stored.munge_key = self._slurm_manager.get_munge_key()
        self._stored.slurm_installed = True
        self.unit.status = ActiveStatus("Slurm Installed")

    def _on_upgrade(self, event):
        self._slurm_manager.upgrade()

    def _on_check_status_and_write_config(self, event):
        if not self._check_status():
            event.defer()
            return

        slurm_config = self._assemble_slurm_config()
        if not slurm_config:
            event.defer()
            return

        self._slurmd.set_slurm_config_on_app_relation_data(
            'slurmd',
            slurm_config,
        )

        self._slurmctld.set_slurm_config_on_app_relation_data(
            'slurmctld',
            slurm_config,
        )

        if self._stored.slurmrestd_available:
            self._slurmrestd.set_slurm_config_on_app_relation_data(
                'slurmrestd',
                slurm_config,
            )

    def _on_provide_slurmrestd(self, event):
        if not self._check_status():
            event.defer()
            return

        slurm_config = self._assemble_slurm_config()
        if not slurm_config:
            event.defer()
            return

        self._slurmrestd.set_slurm_config_on_app_relation_data(
            'slurmrestd',
            slurm_config,
        )

    def _assemble_slurm_config(self):
        """Assemble and return the slurm config."""
        slurmd_info = self._slurmd.get_slurmd_info()
        slurmdbd_info = self._slurmdbd.get_slurmdbd_info()
        slurmctld_info = self._slurmctld.get_slurmctld_info()

        elasticsearch_endpoint = self._stored.elasticsearch_ingress

        nhc_info = self._stored.nhc_info

        ctxt = {
            'nhc': {},
            'elasticsearch_address': "",
        }
        if nhc_info:
            ctxt['nhc']['nhc_bin'] = nhc_info['nhc_bin']
            ctxt['nhc']['health_check_interval'] = \
                nhc_info['health_check_interval']
            ctxt['nhc']['health_check_node_state'] = \
                nhc_info['health_check_node_state']

        if elasticsearch_endpoint:
            ctxt['elasticsearch_address'] = elasticsearch_endpoint

        return {
            'slurmd_info': slurmd_info,
            **slurmctld_info,
            **slurmdbd_info,
            **ctxt,
        }

    def _check_status(self):
        slurmctld_available = self._stored.slurmctld_available
        slurmd_available = self._stored.slurmd_available
        slurmdbd_available = self._stored.slurmdbd_available
        slurm_installed = self._stored.slurm_installed

        if not (slurmdbd_available and slurmd_available and
                slurmctld_available and slurm_installed):
            if not slurmctld_available:
                self.unit.status = BlockedStatus("NEED RELATION TO SLURMCTLD")
            if not slurmd_available:
                self.unit.status = BlockedStatus("NEED RELATION TO SLURMD")
            elif not slurmdbd_available:
                self.unit.status = BlockedStatus("NEED RELATION TO SLURMDBD")
            else:
                self.unit.status = BlockedStatus("SLURM NOT INSTALLED")
            return False
        else:
            self.unit.status = ActiveStatus("")
            return True

    def is_slurmd_available(self):
        """Return slurmd_available."""
        return self._stored.slurmd_available

    def is_slurmctld_available(self):
        """Return slurmctld_acquired from local stored state."""
        return self._stored.slurmctld_available

    def is_slurmdbd_available(self):
        """Return slurmdbd_available."""
        return self._stored.slurmdbd_available

    def is_slurmrestd_available(self):
        """Return slurmrestd_available."""
        return self._stored.slurmrestd_available

    def is_slurm_installed(self):
        """Return true/false based on whether or not slurm is installed."""
        return self._stored.slurm_installed

    def get_munge_key(self):
        """Return the slurmdbd_info from stored state."""
        return self._stored.munge_key

    def set_nhc_info(self, nhc_info):
        """Set the nhc_info to _stored."""
        self._stored.nhc_info = nhc_info

    def set_elasticsearch_ingress(self, elasticsearch_ingress):
        """Set elasticsearch_ingress to _stored."""
        self._stored.elasticsearch_ingress = elasticsearch_ingress

    def set_slurmd_available(self, slurmd_available):
        """Set slurmd_available."""
        self._stored.slurmd_available = slurmd_available

    def set_slurmctld_available(self, slurmctld_available):
        """Set slurmctld_available."""
        self._stored.slurmctld_available = slurmctld_available

    def set_slurmdbd_available(self, slurmdbd_available):
        """Set slurmdbd_available."""
        self._stored.slurmdbd_available = slurmdbd_available

    def set_slurmrestd_available(self, slurmrestd_available):
        """Set slurmrestd_available."""
        self._stored.slurmrestd_available = slurmrestd_available


if __name__ == "__main__":
    main(SlurmConfiguratorCharm)
