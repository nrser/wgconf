from __future__ import annotations
from collections import abc

from nansi.plugins.action.compose import ComposeAction
from nansi.utils.collections import dig

def has_partitions(disk):
    return disk['partition_count'] > 0

def is_empty_partition(partition):
    return (
        'drive_letter' in partition and
        'volumes' in partition and
        isinstance(partition['volumes'], abc.Sequence) and
        len(partition['volumes']) == 1 and
        dig(partition, 'volumes', 0, 'size') == 0
    )

class ActionModule(ComposeAction):
    def fetch_disks(self):
        result = self.tasks['community.windows.win_disk_facts']()
        return result['ansible_facts']['ansible_disks']

    def initialize_disk(self, disk):
        self.log.debug(f"Initializing disk {disk['number']}...")
        return self.tasks['community.windows.win_initialize_disk'](
            disk_number = disk['number'],
            style       = 'mbr',
        )

    def partition_disk(self, disk):
        self.log.debug(f"Partitioning disk {disk['number']}...")
        return self.tasks['community.windows.win_partition'](
            disk_number         = disk['number'],
            partition_number    = 1,
            partition_size      = -1, # Full-capacity
            drive_letter        = 'auto',
            active              = False,
        )

    def format_partition(self, disk, partition):
        self.log.debug(
            f"Formatting disk {disk['number']}, "
            f"partition {partition['number']}..."
        )
        return self.tasks['community.windows.win_format'](
            drive_letter    = partition['drive_letter'],
            file_system     = 'NTFS',
            new_label       = f"disk-{disk['number']}-{partition['number']}",
            force           = True,
        )

    def compose(self):
        disks = self.fetch_disks()

        to_partition = [d for d in disks if not has_partitions(d)]

        for disk in to_partition:
            self.initialize_disk(disk)
            self.partition_disk(disk)

        if len(to_partition) > 0:
            # Re-read facts so the next part works right
            disks = self.fetch_disks()

        # Format any un-formatted partitions
        for disk in (d for d in disks if 'partitions' in d):
            for partition in disk['partitions']:
                if is_empty_partition(partition):
                    self.format_partition(disk, partition)
