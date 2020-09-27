#!/usr/bin/python3
"""SlurmdCharm."""
import logging

from interface_slurmd import Slurmd
from interface_slurmd_peer import SlurmdPeer
from ops.charm import CharmBase
from ops.framework import StoredState
from ops.main import main
from ops.model import (
    ActiveStatus,
    BlockedStatus,
)
from slurm_ops_manager import SlurmManager


logger = logging.getLogger()


class SlurmdCharm(CharmBase):
    """Slurmd lifecycle events."""

    _stored = StoredState()

    def __init__(self, *args):
        """Init _stored attributes and interfaces, observe events."""
        super().__init__(*args)

        self._stored.set_default(
            munge_key=str(),
            slurm_configurator_available=False,
        )

        self._slurm_manager = SlurmManager(self, "slurmd")

        self._slurmd = Slurmd(self, "slurmd")
        self._slurmd_peer = SlurmdPeer(self, "slurmd-peer")

        event_handler_bindings = {
            self.on.install: self._on_install,

            self.on.start:
            self._on_check_status_and_write_config,

            self.on.config_changed:
            self._on_check_status_and_write_config,

            self.on.upgrade_charm: self._on_upgrade,

            self._slurmd_peer.on.slurmd_peer_available:
            self._on_send_slurmd_info,

            self._slurmd.on.slurm_config_available:
            self._on_check_status_and_write_config,
        }
        for event, handler in event_handler_bindings.items():
            self.framework.observe(event, handler)

    def _on_install(self, event):
        self._slurm_manager.install()
        self._stored.slurm_installed = True
        self.unit.status = ActiveStatus("Slurm Installed")

    def _on_upgrade(self, event):
        self._slurm_manager.upgrade()

    def _on_send_slurmd_info(self, event):
        if self.model.unit.is_leader():
            self._slurmd.set_slurmd_info_on_app_relation_data(
                self._assemble_slurmd_info()
            )

    def _on_check_status_and_write_config(self, event):
        if not self._check_status():
            event.defer()
            return

    def _check_status(self):
        slurm_configurator = self._stored.slurm_configurator_available
        if not slurm_configurator:
            self.unit.status = BlockedStatus(
                "Waiting on slurm-configurator relation."
            )
            return False
        return True

    def _assemble_slurmd_info(self):
        """Get the slurmd inventory and assemble the partition."""
        slurmd_info = self._slurmd_peers.get_slurmd_info()

        partition_name = self.model.config.get('partition-name')
        partition_config = self.model.config.get('partition-config')
        partition_state = self.model.config.get('partition-state')

        return {
            'inventory': slurmd_info,
            'partition_name': partition_name,
            'partition_state': partition_state,
            'partition_config': partition_config,
        }

    def set_slurm_configurator_available(self, slurm_configurator_available):
        """Set slurm_configurator_available."""
        self._stored.slurm_configurator_available = \
            slurm_configurator_available

    def set_munge_key(self, munge_key):
        """Set the munge key."""
        self._stored.munge_key = munge_key

    def set_slurm_config(self, slurm_config):
        """Set the slurm config."""
        self._stored.slurm_conifg = slurm_config

    def get_hostname(self):
        """Return the hostname."""
        return self._slurm_manager.hostname

    def get_port(self):
        """Return the port."""
        return self._slurm_manager.port


if __name__ == "__main__":
    main(SlurmdCharm)
