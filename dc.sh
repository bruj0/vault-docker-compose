#!/bin/bash -e
# To enable debug: export DEBUG=true

#Functions
function vault_unseal {
    echo "Unsealing it"
    eval var=( \${VAULT_${VAULT_CLUSTER}_PORTS[@]} ) ;
    if [[ "$1" == "secondary" ]]; then
        export VAULT_DATA="vault/api"
    fi
    for port in "${var[@]}"; do
        VAULT_ADDR="http://127.0.0.1:${port}" yapi yapi/vault/02-unseal.yaml --debug
    done
}
# Enable debug if the env variable DEBUG is set to true
if [[ "$DEBUG" == "true" ]];then
    set -x
fi

case $1 in
    "proxy")
    ;;
    "wipe")
    ;;
    *)
        # Initial checking
        if [[ -z "${CLUSTER}" ]]; then
            echo "Error: CLUSTER is not set"
            exit 0
        fi
    ;;
esac

#External variables used by other scripts
export VAULT_CLUSTER=${CLUSTER}
export CONSUL_CLUSTER=${CLUSTER}
export COMPOSE_PROJECT_NAME=${CLUSTER}

#Internal variables
typeset -a VAULT_primary_PORTS=("9201" "9202" "9203")
typeset -a VAULT_secondary_PORTS=("9301" "9302" "9303")
typeset -a VAULT_dr_PORTS=("9401" "9402" "9403")
ROOT=$(pwd)
SLEEP_TIME=1
CLUSTER_DIR=${CLUSTER}

case $CLUSTER in
    "primary")
        CLUSTER_DIR="."
        export VAULT_ADDR=http://127.0.0.1:9201
    ;;
    "secondary")
        export VAULT_ADDR=http://127.0.0.1:9301
    ;;
    "dr")
        export VAULT_ADDR=http://127.0.0.1:9401
    ;;
esac

export VAULT_DATA="${CLUSTER_DIR}/vault/api"
COMPOSE_CMD="docker-compose -f ${CLUSTER_DIR}/docker-compose.${CLUSTER}.yml -f docker-compose.yml"



#Main logic
#wipe command
#deletes consul data directories
case "$1" in
    "config")
        ${COMPOSE_CMD} config
    ;;
    "wipe")
        echo "Wiping consul data.."
        rm -r consul/data/
        rm -r secondary/consul/data/
        rm -r dr/consul/data/
    ;;
    "up")
#up command
#also initializes if there is no init.json under yapi/vault/$CLUSTER
        echo "Starting up $CLUSTER"
        if [ "$1" == "recreate" ]; then
            RECREATE="--force-recreate"
            echo "* Forcing recreate"
        fi
        echo "Starting consul server bootstrap"
        ${COMPOSE_CMD} up -d consul_server_bootstrap ${RECREATE}
        echo "Waiting for startup"
        sleep ${SLEEP_TIME}

        echo "Starting consul server 1"
        ${COMPOSE_CMD} up -d consul_server_1 ${RECREATE}
        echo "Waiting for startup"
        sleep ${SLEEP_TIME}

        echo "Starting consul server 2"
        ${COMPOSE_CMD} up -d consul_server_2 ${RECREATE}
        echo "Waiting for startup"
        sleep ${SLEEP_TIME}

        echo "Starting consul agent 1"
        ${COMPOSE_CMD} up -d consul_agent_1 ${RECREATE}
        echo "Waiting for startup"
        sleep ${SLEEP_TIME}

        echo "Starting consul agent 2"
        ${COMPOSE_CMD} up -d consul_agent_2 ${RECREATE}
        echo "Waiting for startup"
        sleep ${SLEEP_TIME}

        echo "Starting consul agent 3"
        ${COMPOSE_CMD} up -d consul_agent_3 ${RECREATE}
        echo "Waiting for startup"
        sleep ${SLEEP_TIME}

        SLEEP_TIME=$(( $SLEEP_TIME + ( $SLEEP_TIME * 2) ))
        echo "Starting Vault server 1"
        ${COMPOSE_CMD} up -d vault01 ${RECREATE}
        echo "Waiting for startup"
        sleep ${SLEEP_TIME}

        echo "Starting Vault server 2"
        ${COMPOSE_CMD} up -d vault02 ${RECREATE}
        echo "Waiting for startup"
        sleep ${SLEEP_TIME}

        echo "Starting Vault server 3"
        ${COMPOSE_CMD} up -d vault03 ${RECREATE}
        echo "Waiting for startup"
        sleep ${SLEEP_TIME}


        # Initializaing and Unsealing
        if [ ! -f "$VAULT_DATA/init.json" ]; then
            echo "Initializing Vault cluster ${CLUSTER} at ${VAULT_ADDR}, files stored in ${VAULT_DATA}"
            yapi yapi/vault/01-init.yaml --debug
        fi

        vault_unseal
    ;;

    "enable_secondary")
        export VAULT_TOKEN=$(cat ${VAULT_DATA}/init.json | jq -r '.root_token')
        export SECONDARY_HAPROXY_ADDR=$(docker network inspect vault_secondary | jq -r '.[] .Containers | with_entries(select(.value.Name=="haproxy"))| .[] .IPv4Address' | awk -F "/" '{print $1}')

        echo "Enabling replication in primary"
        yapi yapi/vault/03-replication_enable_primary.yaml --debug

        echo "Creating secondary JWT token id=secondary"
        yapi yapi/vault/04-replication_secondary_token.yaml --debug
        
        echo "Enabling secondary replication to primary"
        VAULT_TOKEN_SEC=$(cat secondary/${VAULT_DATA}/init.json | jq -r '.root_token')
        VAULT_ADDR=http://127.0.0.1:9301 VAULT_TOKEN=${VAULT_TOKEN_SEC} \
        yapi yapi/vault/05-replication_activate_secondary.yaml --debug

        echo "Creating a root token for secondary with the new unseal keys"
        VAULT_ADDR=http://127.0.0.1:9301 VAULT_DATA_KEYS="vault/api" \
        yapi yapi/vault/06-replication_generate_root_secondary.yaml --debug
    
    ;;
    "down")
#down command
#also initializes if there is no init.json under yapi/vault/$CLUSTER
        ${COMPOSE_CMD} down
    ;;

    "proxy")
# proxy command
        if [[ $2 == "start" ]]; then
            pwd=$(pwd)
            cd proxy
            docker-compose up -d
        fi
    ;;
    "restart")
# Restart command
# if service start with vault then run vaul_seal func.
        case "$2" in
            "vault")
                ${COMPOSE_CMD} restart vault01 vault02 vault03
                pwd=$(pwd)
                cd ${ROOT}/yapi/vault
                vault_unseal
                cd ${pwd}
            ;;
            "proxy")
                cd proxy
                docker-compose restart
            ;;
            *)
                ${COMPOSE_CMD} restart $2
            ;;
        esac
    ;;
    "unseal")
# unseal command
# if replication is given as a parameter the primary unsealing key will be used
        if [[ $2 == "replication" ]]; then
            vault_unseal primary
        else
            vault_unseal
        fi
    ;;
    "cli")
# Cli command
# $2 vault or consul or show
# $3 command
        export VAULT_TOKEN=$(cat ${VAULT_DATA}/init.json | jq -r '.root_token')
        case "$2" in
            "vault")
                vault ${@:3}
                ;;
            "yapi")
                 yapi ${@:3}
                ;;
            "vars")
                set +x
                echo "Exporting variables for ${CLUSTER}"
                echo "export VAULT_ADDR=\"${VAULT_ADDR}\""
                echo "export VAULT_DATA=\"${VAULT_DATA}\""
                echo "export VAULT_TOKEN=\"${VAULT_TOKEN}\""
                ;;
            *)
            echo "Cli not implemented: $2"
            exit 1   
            esac
    ;;
    *)
    echo "Unknown command: $1"
    cd ${ROOT}
    exit 1
esac

cd ${ROOT}

