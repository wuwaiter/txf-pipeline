#!/bin/bash
# 自動建立 monitoring bucket (若已存在則略過)
influx bucket create \
  --name monitoring \
  --org "${DOCKER_INFLUXDB_INIT_ORG}" \
  --token "${DOCKER_INFLUXDB_INIT_ADMIN_TOKEN}" \
  --retention 0 2>/dev/null || echo "Bucket 'monitoring' already exists, skipping."
