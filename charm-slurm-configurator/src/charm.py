#!/usr/bin/python3
"""SlurmctldCharm."""
import copy
import logging

from interface_slurmctld import Slurmctld
from interface_slurmd import Slurmd
from interface_slurmdbd import Slurmdbd
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
            default_partition=str(),
            munge_key=str(),
            slurm_installed=False,
            slurmctld_available=False,
            slurmdbd_available=False,
            slurmd_available=False,
        )

        self._slurm_manager = SlurmManager(self, "slurmd")

        self._slurmctld = Slurmctld(self, "slurmctld")
        self._slurmdbd = Slurmdbd(self, "slurmdbd")
        self._slurmd = Slurmd(self, "slurmd")

        event_handler_bindings = {
            self.on.install: self._on_install,


            self.on.config_changed:
            self._on_check_status_and_write_config,

            self.on.upgrade_charm: self._on_upgrade,

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

            self._slurmd.on.slurmd_unavailable:
            self._on_check_status_and_write_config,
        }
        for event, handler in event_handler_bindings.items():
            self.framework.observe(event, handler)

    def _on_install(self, event):
        """Install the slurm snap and set the munge key."""
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

        self._slurmctld.set_slurm_config_on_app_relation_data(
            slurm_config,
        )

        self._slurmd.set_slurm_config_on_app_relation_data(
            slurm_config,
        )

    def _assemble_slurm_config(self):
        """Assemble and return the slurm config."""
        slurmctld_info = self._slurmctld.get_slurmctld_info()
        slurmdbd_info = self._slurmdbd.get_slurmdbd_info()
        slurmd_info = self._slurmd.get_slurmd_info()

        if not (slurmd_info and slurmctld_info and slurmdbd_info):
            return None

        logger.debug(slurmctld_info)
        logger.debug(slurmdbd_info)
        logger.debug(slurmd_info)

        ctxt = {
            'nhc': {},
            'elasticsearch_address': "",
        }

        slurmd_info_tmp = copy.deepcopy(slurmd_info)

        for partition in slurmd_info:
            partition_tmp = copy.deepcopy(partition)
            if partition['partition_name'] == self._stored.default_partition:
                partition_tmp['partition_default'] = 'YES'
                slurmd_info_tmp.remove(partition)
                slurmd_info_tmp.append(partition_tmp)

        return {
            'slurmd_info': slurmd_info_tmp,
            **slurmctld_info,
            **slurmdbd_info,
            **ctxt,
        }

    def _check_status(self):
        slurmctld_available = self._stored.slurmctld_available
        slurmdbd_available = self._stored.slurmdbd_available
        slurmd_available = self._stored.slurmd_available
        slurm_installed = self._stored.slurm_installed

        deps = [
            slurmctld_available,
            slurmdbd_available,
            slurmd_available,
            slurm_installed,
        ]

        if not all(deps):
            if not slurmctld_available:
                self.unit.status = BlockedStatus("NEED RELATION TO SLURMCTLD")
            elif not slurmdbd_available:
                self.unit.status = BlockedStatus("NEED RELATION TO SLURMDBD")
            elif not slurmd_available:
                self.unit.status = BlockedStatus("NEED RELATION TO SLURMD")
            else:
                self.unit.status = BlockedStatus("SLURM NOT INSTALLED")
            return False
        else:
            self.unit.status = ActiveStatus("")
            return True

    def is_slurm_installed(self):
        """Return true/false based on whether or not slurm is installed."""
        return self._stored.slurm_installed

    def get_munge_key(self):
        """Return the slurmdbd_info from stored state."""
        return self._stored.munge_key

    def get_default_partition(self, partition_name):
        """Get self._stored.default_partition."""
        return self._stored.default_partition

    def set_slurmctld_available(self, slurmctld_available):
        """Set slurmctld_available."""
        self._stored.slurmctld_available = slurmctld_available

    def set_slurmdbd_available(self, slurmdbd_available):
        """Set slurmdbd_available."""
        self._stored.slurmdbd_available = slurmdbd_available

    def set_default_partition(self, partition_name):
        """Set self._stored.default_partition."""
        self._stored.default_partition = partition_name

    def set_slurmd_available(self, slurmd_available):
        """Set slurmd_available."""
        self._stored.slurmd_available = slurmd_available


if __name__ == "__main__":
    main(SlurmConfiguratorCharm)
