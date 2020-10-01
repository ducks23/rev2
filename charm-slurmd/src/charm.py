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
            user_node_state=str(),
        )

        self._slurm_manager = SlurmManager(self, "slurmd")

        self._slurmd = Slurmd(self, "slurmd")
        self._slurmd_peer = SlurmdPeer(self, "slurmd-peer")

        event_handler_bindings = {
            self.on.install: self._on_install,
            self.on.upgrade_charm: self._on_upgrade,

            self.on.start:
            self._on_check_status_and_write_config,

            self.on.config_changed:
            self._on_send_slurmd_info,

            self._slurmd_peer.on.slurmd_peer_available:
            self._on_send_slurmd_info,

            self._slurmd.on.slurm_config_available:
            self._on_check_status_and_write_config,

            self.on.node_state_action:
            self._on_node_state_action,
        }
        for event, handler in event_handler_bindings.items():
            self.framework.observe(event, handler)


    def _on_node_state_action(self, event):
        """Set the node state."""
        self._stored.user_node_state = event.params["node-state"]
        self._on_send_slurm_info(event)

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

        user_node_state = self._stored.user_node_state
        if user_node_state:
            user_node_states = {
                item.split("=")[0]: item.split("=")[1]
                for item in user_node_state.split(",")
            }

            slurmd_info_tmp = copy.deepcopy(slurmd_info)

            for partition in slurmd_info:
                partition_tmp = copy.deepcopy(partition)
                for slurmd_node in partition['inventory']:
                    if slurmd_node['hostname'] in user_node_states.keys():
                        slurmd_node_tmp = copy.deepcopy(slurmd_node)
                        slurmd_node_tmp['state'] = user_node_states[slurmd_node['hostname']]
                        partition_tmp['inventory'].remove(slurmd_node)
                        partition_tmp['inventory'].append(slurmd_node_tmp)
                slurmd_info_tmp.remove(partition)
                slurmd_info_tmp.append(partition_tmp)
        else:
            slurmd_info_tmp = slurmd_info

        partition_name = self.model.config.get('partition-name')
        if partition_name:
            partition_name_tmp = partition_name
        else:
            if not self._stored.partition_name:
                def random_string(length=10):
                    random_str = ""
                    for i in range(length):
                        random_integer = random.randint(97, 97 + 26 - 1)
                        flip_bit = random.randint(0, 1)
                        random_integer = random_integer - 32 if flip_bit == 1 else random_integer
                        random_str += (chr(random_integer))
                self._stored.partition_name = f"juju-compute-{random_string()}"
            partition_name_tmp = self._stored.partition_name

        partition_config = self.model.config.get('partition-config')
        partition_state = self.model.config.get('partition-state')

        return {
            'inventory': slurmd_info_tmp,
            'partition_name': partition_name_tmp,
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
