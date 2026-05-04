#!/usr/bin/env bash
set -euo pipefail

SERVICE_NAME="${SERVICE_NAME:-telegram-api-proxy}"
UNIT_FILE="/etc/systemd/system/${SERVICE_NAME}.service"

if [[ "${EUID}" -ne 0 ]]; then
    echo "Please run this script with sudo."
    exit 1
fi

if systemctl list-unit-files | grep -q "^${SERVICE_NAME}\.service"; then
    systemctl stop "$SERVICE_NAME" || true
    systemctl disable "$SERVICE_NAME" || true
fi

if [[ -f "$UNIT_FILE" ]]; then
    rm -f "$UNIT_FILE"
fi

systemctl daemon-reload

echo "Uninstalled service: $SERVICE_NAME"
echo "Removed unit file: $UNIT_FILE"