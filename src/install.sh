#! /bin/sh
#
# install.sh
# Copyright (C) 2023 root <root@release-monitoring>
#
# Distributed under terms of the MIT license.
#



cat << EOF > /etc/systemd/system/report-monitoring.service
[Unit]
Description=Generate report for packages versions

[Service]
Type=oneshot
ExecStart=$(realpath report.sh)
User=root
EOF

cat << EOF > /etc/systemd/system/report-monitoring.timer
[Unit]
Description=Run report-monitoring weekly

[Timer]
OnCalendar=Mon 3:00
Persistent=true

[Install]
WantedBy=timers.target
EOF

systemctl start report-monitoring.timer
