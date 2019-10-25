#!/bin/bash
CLUSTER=primary
export VAULT_CLUSTER=${CLUSTER}
export CONSUL_CLUSTER=${CLUSTER}
export COMPOSE_PROJECT_NAME=${CLUSTER}
docker-compose -f docker-compose.${CLUSTER}.yml -f docker-compose.yml $@
