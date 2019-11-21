# The What
A way to create multiple Vault clusters and setup different types of Replication between them as close as possible to the "Vault reference architecture" https://learn.hashicorp.com/vault/operations/ops-reference-architecture

Using the 3 Region setup architecture:

![3 regions](https://d33wubrfki0l68.cloudfront.net/f4320f807477cdda5df25f904eaf3d7c9cfd761d/e6047/static/img/vault-ra-full-replication_no_region.png)

Each `Region` is composed of a docker network and has a set of Vault and Consul clusters.

They can only communicate with each other using a `proxy` (sometimes incorrectly called Load Balancer) in this case `HAProxy`.
- Region 1 contains the `Primary` Vault cluster, configured following the [Deployment Guide](https://learn.hashicorp.com/vault/day-one/ops-deployment-guide)  
- Region 2 contains the `Secondary` Vault cluster, configured as [Performance Replication](https://learn.hashicorp.com/vault/operations/ops-replication)
- Region 3 will contain a `DR` Vault cluster configured as [Disaster Recovery](https://learn.hashicorp.com/vault/operations/ops-disaster-recovery)
  
All regions have a Consul cluster for storage and every Vault node has a `Consul Agent` in a different container.

# Why 
To be able to easily setup and test different configuration and features of a full fledge Vault and Consul cluster setup.

# Requirements or the How
* Docker 
* Docker-compose:
  *  Scheduling of containers
  *  Overlaying of configuration to avoid duplication
* [Yapi-ci](https://github.com/bruj0/yapi)
  * Initialization
  * API management
* Access to Premium or Pro version of Vault
* `vault` and `jq` binaries installed in the $PATH
 
     
To talk to Vault we will use `Yapi-ci`, this is a yaml file where we define how the API call will look like.

The benefits over a bash script using `curl` is that we can manipulate the response and its very clear what the call does.

You can take a look at them under `yapi/vault`, for example:
```yaml
---
test_name: 01-Enable primary
stages:
  - name: 01-Enable primary
    request:
      url: "{env_vars.VAULT_ADDR}/v1/sys/replication/performance/primary/enable"
      method: POST
      headers:
        X-Vault-Token: "{env_vars.VAULT_TOKEN}"      
      json:
        primary_cluster_addr: "{env_vars.PRIMARY_HAPROXY_ADDR}"
    response:
      status_code: 200
```


## Networks or Regions
It uses 3 networks:
* vault_primary
* vault_secondary
* vault_dr
  
Each network hosts this configuration of servers (currently only 3 Consul nodes):

![Single availability zone](https://d33wubrfki0l68.cloudfront.net/177ba67519ffb1c802f5cb699c0b70cb40533ab6/63838/static/img/vault-ra-1-az.png)

## Communication between them

It uses an HAProxy instance in TCP mode by accessing the IP trough consul SRV DNS record but this can be changed to any type of service discovery supported by HAProxy.

![proxy](https://d33wubrfki0l68.cloudfront.net/b2d787641bf2dda0a8a1abf691cd9723a9c0ed8c/7b419/static/img/vault-ref-arch-9.png)


## Initial configuration

- Create the docker networks
```bash
$ docker network create {vault_primary,vault_secondary,vault_dr}
```
## Install yapi

```bash
$ pip install -U yapi-ci
$ yapi --version
0.1.6
```

## Start the clusters
```bash
$ CLUSTER=primary ./dc.sh up
$ ./dc.sh proxy start
$ CLUSTER=secondary ./dc.sh up
```

## Start replication
If you want to do it manually go [here](#how-to-manually-configure-performance-replication): 

```bash
$ CLUSTER=primary ./dc.sh enable_secondary
```
## Check that replication is up
```bash
$ env CLUSTER=primary ./dc.sh cli vault read sys/replication/performance/status
Key                     Value
---                     -----
cluster_id              2cc7aad6-026a-9620-6f0d-1e8fa939a11e
known_secondaries       [secondary]
last_reindex_epoch      0
last_wal                247
merkle_root             d85e48c2ec44b1e6ba6671773ea26d836b64ed09
mode                    primary
primary_cluster_addr    https://172.25.0.2:8201
state                   running

$ env CLUSTER=secondary ./dc.sh cli vault read sys/replication/performance/status
Key                            Value
---                            -----
cluster_id                     2cc7aad6-026a-9620-6f0d-1e8fa939a11e
known_primary_cluster_addrs    [https://172.24.0.8:8201 https://172.24.0.9:8201 https://172.24.0.10:8201]
last_reindex_epoch             1574351423
last_remote_wal                0
merkle_root                    d85e48c2ec44b1e6ba6671773ea26d836b64ed09
mode                           secondary
primary_cluster_addr           https://172.25.0.2:8201
secondary_id                   secondary
state                          stream-wals
```

### Commands supported
All the commands read the `CLUSTER` variable to determine where is the operation going to run on.

Example:
```bash
$ CLUSTER=primary ./dc.sh cli vault status
Key             Value
---             -----
Seal Type       shamir
Initialized     true
Sealed          false
Total Shares    1
Threshold       1
Version         1.2.3+prem
Cluster Name    Primary
Cluster ID      a10b1027-e814-3b46-ae07-55581008e1eb
HA Enabled      true
HA Cluster      https://172.24.0.9:8201
HA Mode         active
Last WAL        257
```
- `config`: Will execute `docker-compose config` with the proper templates 
- `up`: This will start the Vault and Consul cluster up for the specified type of cluster by doing a `docker-compose up -d`

- `down`: It will do a `docker-compose down` with the correct template

- `wipe`: Will wipe ALL the consul data files, make sure to do it after `down`

- `restart`
  - vault
  - consul
  - proxy

- `cli`: This will set the variables `VAULT_TOKEN` from `vault/api/init.json` and `VAULT_ADDR` to the port of the first node of the selected cluster.
  - `vars`: Prints variables for the given cluster 
```bash
$ env CLUSTER=primary ./dc.sh cli vars                                                                                        Exporting variables for primary
export VAULT_ADDR="http://127.0.0.1:9201"
export VAULT_DATA="./vault/api"
export VAULT_TOKEN="s.YFfiUgyPCZAtJIQ55NtvVa2K"
```
  - `vault <command>`
  - `yapi <template file>[--debug]`

- `unseal`
  - replication: if this argument is given the primary unseal key will be used instead

- `proxy`
  - start

## How `dc.sh` works
*This is all automated with the `up` command and its here for documentation purposes.*

- Each cluster has its own directory:
  * Primary -> /
  * Secondary -> secondary
  * DR -> dr
- Each directory has this structure:
  - `consul`
    - `data`

This will contain the directories where each consul server will store its data:
`consul01 consul02 consul03`.

Each of this directories are mount at `/consul/data` inside the respective container

  - `config` : This is mounted inside the containers as /consul/config
  - `vault`
    - `config`: Mounted at `/vault/config` 
    - `api`: Where the response from the API is stored, ie unseal keys and root token
    - `logs`: Where the audit logs will be stored.

## How to manually configure performance replication

1. Set the correct environmental variables, you can get them from the output of this command.
```bash
$ env CLUSTER=primary ./dc.sh cli vars
Exporting variables for primary
export VAULT_ADDR="http://127.0.0.1:9201"
export VAULT_DATA="./vault/api"
export VAULT_TOKEN="s.YFfiUgyPCZAtJIQ55NtvVa2K"
```
2. Enable replication
  
`SECONDARY_HAPROXY_ADDR` is the IP of the network card in the `proxy` container that is connected to the network `vault_secondary`.

We need this IP so that the secondary cluster can contact the primary trough the proxy.

It will be configured as the `primary_cluster_addr` variable in Vault.

```bash
$ export SECONDARY_HAPROXY_ADDR=(docker network inspect vault_secondary | jq -r '.[] .Containers | with_entries(select(.value.Name=="haproxy"))| .[] .IPv4Address' | awk -F "/" '{print $1}')
$ CLUSTER=primary ./dc.sh cli yapi yapi/vault/03-replication_enable_primary.yaml
```
3. Check that the replication was configured correctly:

```json
$ CLUSTER=primary ./dc.sh cli vault read sys/replication/status -format=json
{
  "request_id": "c2e75241-9d82-7d32-41dc-f68998d58610",
  "lease_id": "",
  "lease_duration": 0,
  "renewable": false,
  "data": {
    "dr": {
      "mode": "disabled"
    },
    "performance": {
      "cluster_id": "2cc7aad6-026a-9620-6f0d-1e8fa939a11e",
      "known_secondaries": [
        "secondary"
      ],
      "last_reindex_epoch": "0",
      "last_wal": 63,
      "merkle_root": "ef70ddb8948f4dbbd90980f418195d30acddb0d2",
      "mode": "primary",
      "primary_cluster_addr": "https://172.25.0.2:8201",
      "state": "running"
    }
  },
  "warnings": null
}
```

4. Create secondary token
  
This will save the token to `vault/api/secondary-token.json` and create it with the `id=secondary`

```bash
$ CLUSTER=primary ./dc.sh cli yapi yapi/vault/04-replication_secondary_token.yaml
```

5. Enable replication on the secondary cluster

We dont use `cli yapi` because we are mixing the Vault address of the secondary with the data of the primary.

```bash
$ export VAULT_TOKEN=$(cat secondary/vault/api/init.json | jq -r '.root_token')
$ export VAULT_DATA="vault/api"
$ export VAULT_ADDR="http://127.0.0.1:9301"
$ yapi yapi/vault/05-replication_activate_secondary.yaml
```
This will save the response to `vault/api/enable-secondary-resp.json`

6. Check that the replication is working on the secondary

```json
$ env DEBUG=false CLUSTER=secondary ./dc.sh cli vault read sys/replication/status -format=json
{
  "request_id": "af4cd82c-9b57-0061-1fe1-09f06166bed7",
  "lease_id": "",
  "lease_duration": 0,
  "renewable": false,
  "data": {
    "dr": {
      "mode": "disabled"
    },
    "performance": {
      "cluster_id": "2cc7aad6-026a-9620-6f0d-1e8fa939a11e",
      "known_primary_cluster_addrs": [
        "https://172.24.0.8:8201",
        "https://172.24.0.9:8201",
        "https://172.24.0.10:8201"
      ],
      "last_reindex_epoch": "1573144926",
      "last_remote_wal": 0,
      "merkle_root": "ef70ddb8948f4dbbd90980f418195d30acddb0d2",
      "mode": "secondary",
      "primary_cluster_addr": "https://172.25.0.2:8201",
      "secondary_id": "secondary",
      "state": "stream-wals"
    }
  },
  "warnings": null
}
```

### View the full compose template for a given cluster
```bash
$ export CLUSTER=primary|secondary|dr
$ export VAULT_CLUSTER=${CLUSTER}
$ export CONSUL_CLUSTER=${CLUSTER}
$ export COMPOSE_PROJECT_NAME=${CLUSTER}
$ docker-compose -f docker-compose.${CLUSTER}.yml -f docker-compose.yml up -d 
```

### Initialization of Vault
This will save the unseal keys and root token under the directory ```$CLUSTER_DIR}/vault/api```  as json files.

```bash
$ export VAULT_ADDR=http://127.0.0.1:XXXX
$ export VAULT_data=$CLUSTER_DIR}/vault/api
$ yapi yapi/vault/01-init.yaml
```

### Unsealing
```bash
$ export VAULT_ADDR=http://127.0.0.1:XXXX
$ export VAULT_data=$CLUSTER_DIR}/vault/api
$ yapi yapi/vault/02-unseal.yaml
```
## Troubleshooting

- Make sure the consul cluster is up and running:
```bash
$ CONSUL_HTTP_ADDR=http://127.0.0.1:8500 consul members
$ CONSUL_HTTP_ADDR=http://127.0.0.1:8500 consul operator raft list-peers
$ docker logs -f primary_consul_server_bootstrap_1
```
- Check `haproxy` logs
```bash
$ docker logs -f haproxy
```

## Useful commands

* How to use set the correct VAULT_TOKEN

```bash
$ export VAULT_TOKEN=(cat $CLUSTER_DIR}/vault/api/init.json | jq -r '.root_token')
```

* How to get the network IP of a container

```bash
$ docker network inspect vault_${CLUSTER} | jq -r '.[] .Containers | with_entries(select(.value.Name=="CONTAINER_NAME"))| .[] .IPv4Address' | awk -F "/" '{print $1}'
```


## Exposed ports: local -> container
### Primary
- 8500 -> 8500 (Consul bootstrap server UI)
- 9201 -> 8200 (Vault01 API and UI)
- 9202 -> 8200 (Vault02 API and UI)
- 9203 -> 8200 (Vault03 API and UI)
### Secondary
-  8502 -> 8500 (Consul bootstrap server UI)
-  9301 -> 8200 (Vault01 API and UI)
-  9302 -> 8200 (Vault02 API and UI)
-  9303 -> 8200 (Vault03 API and UI)
### Proxy
- 8801 -> 8200 ( Primary cluster, Active Vault node API )
- 8819 -> 1936 (HAProxy stats)

# TODO
- [x] Initialization and Unsealing with `yapi`
- [X] Configure primary as Performance replication
- [ ] Configure DR cluster
- [X] Create replacement for Tavern
- [X] Better startup handling
- [ ] Add Vault container for PKI
- [ ] Generate PKI certificates and use them
- [ ] Configure Monitoring
- [ ] HSM auto unsealing