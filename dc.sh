#!/bin/bash -xe

#Functions
function vault_unseal {
    echo "Unsealing it"
    eval var=( \${VAULT_${VAULT_CLUSTER}_PORTS[@]} ) ;
    for port in "${var[@]}"; do
        VAULT_ADDR="http://127.0.0.1:${port}" tavern-ci test_unseal.tavern.yaml --debug
    done
}

# Initial checking
if [ -z "${CLUSTER}" ]; then
    echo "Error: CLUSTER is not set"
    exit 0
fi

#Variables setting
typeset -a VAULT_primary_PORTS=("9201" "9202" "9203")
typeset -a VAULT_secondary_PORTS=("9301" "9302" "9303")


export VAULT_CLUSTER=${CLUSTER}
export CONSUL_CLUSTER=${CLUSTER}
export COMPOSE_PROJECT_NAME=${CLUSTER}
MAIN_COMPOSE=docker-compose.yml
ROOT=$(pwd)

if [ "${CLUSTER}" == "primary" ];then
    MAIN_COMPOSE=docker-compose.yml
    export VAULT_ADDR=http://127.0.0.1:9201

elif [ "${CLUSTER}" == "secondary" ];then
    cd ${CLUSTER}
    MAIN_COMPOSE=../docker-compose.yml
    export VAULT_ADDR=http://127.0.0.1:9302

elif [ "${CLUSTER}" == "dr" ];then
    cd ${CLUSTER}
    MAIN_COMPOSE=../docker-compose.yml
    export VAULT_ADDR=http://127.0.0.1:9402

else
    echo "Error: Unknown cluster ${CLUSTER}"
    exit 0
fi

COMPOSE_CMD="docker-compose -f docker-compose.${CLUSTER}.yml -f ${MAIN_COMPOSE}"


#Main logic


#up command
#also initializes if there is no init.json under tavern/vault/$CLUSTER
if [ "$1" == "up" ]; then

    echo "Starting up $CLUSTER"
    if [ "$1" == "recreate" ]; then
        RECREATE="--force-recreate"
        echo "* Forcing recreate"
    fi
    ${COMPOSE_CMD} up -d ${RECREATE}

    # Initializaing and Unsealing
    export PYTHONPATH=${ROOT}/tavern
    cd ${ROOT}/tavern/vault

    if [ ! -f "$CLUSTER/init.json" ]; then
        echo "Initializing Vault cluster ${CLUSTER} at ${VAULT_ADDR}"
        tavern-ci test_init.tavern.yaml --debug
    fi

    vault_unseal

fi

# Restart command
# if service start with vault then run vaul_seal func.
if [[ "$1" == "restart" ]]; then
    if [[ $2 == vault ]]; then
        ${COMPOSE_CMD} restart vault01 vault02 vault03
        pwd=$(pwd)
        cd ${ROOT}/tavern/vault
        vault_unseal
        cd ${pwd}
    else
        ${COMPOSE_CMD} restart $2
    fi
fi

# Cli command
# $2 vault or consul or show
# $3 command

if [[ "$1" == "cli" ]]; then
    if [[ "$2" == "vault" ]]; then
        eval var=( \${VAULT_${VAULT_CLUSTER}_PORTS[@]} ) ;
        VAULT_TOKEN=$(cat ${ROOT}/tavern/vault/${VAULT_CLUSTER}/init.json | jq -r '.root_token') VAULT_ADDR=http://127.0.0.1:${var[0]} vault ${@:3}
    fi
fi
cd ${ROOT}
