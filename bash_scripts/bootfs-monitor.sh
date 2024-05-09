#!/bin/bash

# Define where backups will be stored
backup_dir="/bootbackup"

# Ensure backup directories exist
mkdir -p $backup_dir

# Function to create a disk image and manage old images
backup() {
    local source=$1
    local destination=$2

    /usr/bin/rsync -aAXH --delete $source $destination >> "$backup_dir/backup.log" 2>&1
}

# Function to ensure an initial backup exists
ensure_initial_backup() {
    local source=$1
    local destination=$2

    # Check if any backup files exist for this partition
    if [ $(ls ${destination} 2> /dev/null | wc -l) -eq 0 ]; then
        echo "$(date '+%Y-%m-%d %H:%M:%S') - No backups found for ${source}. Creating initial backup..." >> "$backup_dir/backup.log"
        backup $source $destination
    else
        echo "$(date '+%Y-%m-%d %H:%M:%S') - Initial backup already exists for ${source}." >> "$backup_dir/backup.log"
    fi
}

# Function to monitor and backup with a resettable delay
monitor_and_backup() {
    local monitor_path=$1
    local destination=$2

    # Ensure an initial backup exists
    ensure_initial_backup $monitor_path $destination

    # Monitor file system events and backup on changes
    /usr/bin/inotifywait -m -e modify -e move -e create -e delete -r --format '%w%f' $monitor_path |
    while read event; do
        echo "$(date '+%Y-%m-%d %H:%M:%S') - Change detected at $event" >> "$backup_dir/backup.log"
        backup $monitor_path $destination
    done
}

# Background monitor for each partition
monitor_and_backup "/boot" $backup_dir &
monitor_and_backup "/boot/efi" $backup_dir &

wait
