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
        if self.framework.model.unit.is_leader():
            if self._slurmd.is_joined:
                slurmd_info = self._assemble_slurmd_info()
                if slurmd_info:
                    self._slurmd.set_slurmd_info_on_app_relation_data(
                        slurmd_info
                    )
                    return
            event.defer()
            return

    def _on_check_status_and_write_config(self, event):
        if not self._check_status():
            event.defer()
            return

        slurm_config = self._slurmd.get_slurm_config()
        if not slurm_config:
            event.defer()
            return

        munge_key = self._stored.munge_key
        if not munge_key:
            event.defer()
            return

        self._slurm_manager.render_config_and_restart(
            {**slurm_config, 'munge_key': munge_key}
        )
        self.unit.status = ActiveStatus("Slurmd Available")

    def _check_status(self):
        munge_key = self._stored.munge_key
        slurm_installed = self._stored.slurm_installed
        slurm_config_available = self._slurmd.get_slurm_config()

        if not (munge_key and slurm_installed and slurm_config_available):
            if not munge_key:
                self.unit.status = BlockedStatus(
                    "NEED RELATION TO SLURM CONFIGURATOR"
                )
            elif not slurm_config_available:
                self.unit.status = BlockedStatus(
                    "WAITING ON SLURM CONFIG"
                )
            else:
                self.unit.status = BlockedStatus("SLURM NOT INSTALLED")
            return False
        else:
            return True

    def _assemble_slurmd_info(self):
        """Get the slurmd inventory and assemble the partition."""
        slurmd_info = self._slurmd_peer.get_slurmd_info()
        if not slurmd_info:
            return None

        partition_name = self.model.config.get('partition-name')
        partition_config = self.model.config.get('partition-config')
        partition_state = self.model.config.get('partition-state')

        return {
            'inventory': slurmd_info,
            'partition_name': partition_name,
            'partition_state': partition_state,
            'partition_config': partition_config,
        }

    def set_munge_key(self, munge_key):
        """Set the munge key."""
        self._stored.munge_key = munge_key

    def get_hostname(self):
        """Return the hostname."""
        return self._slurm_manager.hostname

    def get_port(self):
        """Return the port."""
        return self._slurm_manager.port


if __name__ == "__main__":
    main(SlurmdCharm)
