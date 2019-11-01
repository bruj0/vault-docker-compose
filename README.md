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
* [Tavern-ci](https://taverntesting.github.io/)
  * Initialization
  * API management
* Access to Premium or Pro version of Vault
 
     
To talk to Vault we will use `Tavern-ci`, this is a yaml file where we define how the API call will look lik.

The benefits over a bash script using `curl` is that we can manipulate the response and its very clear what the call does.

You can take a look at them under `tavern/vault`, for example:
```yaml
---
test_name: 01-Enable primary
stages:
  - name: 01-Enable primary
    request:
      url: "{tavern.env_vars.VAULT_ADDR}/v1/sys/replication/performance/primary/enable"
      method: POST
      headers:
        X-Vault-Token: "{tavern.env_vars.VAULT_TOKEN}"      
      json:
        primary_cluster_addr: "{tavern.env_vars.PRIMARY_HAPROXY_ADDR}"
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


## Starting it

This is handled by the `dc.sh` script:
```
$ CLUSTER=primary ./dc.sh up
$ ./dc.sh proxy start
$ CLUSTER=secondary ./dc.sh up
```

### Other commands supported
All the commands read the `CLUSTER` variable to determine where is the operation going to run on.

Example:
```
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
- `up`
  - This will start the Vault and Consul cluster up for the specified type of cluster by doing a `docker-compose up -d`

- `down`
  - It will do a `docker-compose down` with the correct template
  - 
- `restart`
  - vault
  - consul
  - proxy

- `cli`
  - vault <command>
  - consul (not implemented yet)

- `unseal`
  - replication (if this argument is given the primary unseal key will be used instead)

- `proxy`
  - start

## How `dc.sh` works
*This is all automated with the `up` command and its here for documentation purposes.*

- To bring up the docker containers, go to the directory for the cluster:
  * Primary -> /
  * Secondary -> secondary
  * DR -> dr
  
    Execute:

    ```
    $ export CLUSTER=primary|secondary|dr
    $ export VAULT_CLUSTER=${CLUSTER}
    $ export CONSUL_CLUSTER=${CLUSTER}
    $ export COMPOSE_PROJECT_NAME=${CLUSTER}
    $ docker-compose -f docker-compose.${CLUSTER}.yml -f docker-compose.yml up -d 
    ```
- Initialization of Vault
    This will save the unseal keys and root token under the directory ```tavern/vault/${VAULT_CLUSTER}```  as json files.
    ```
    $ cd tavern/vault
    $ export VAULT_ADDR=http://127.0.0.1:XXXX
    $ export VAULT_CLUSTER=primary|secondary|dr
    $ tavern-ci test_init.tavern.yaml 
    ```
- Unsealing, go to the `tavern/vault` directory and execute
    ```
    $ export VAULT_CLUSTER=${CLUSTER}
    $ VAULT_ADDR="http://127.0.0.1:${port}"
    $ tavern-ci test_unseal.tavern.yaml --debug
    $ tavern-ci test_init.tavern.yaml --debug
    ```
## Troubleshooting

- Make sure the consul cluster is up and running:
    ```
    $ CONSUL_HTTP_ADDR=http://127.0.0.1:8500 consul members
    $ CONSUL_HTTP_ADDR=http://127.0.0.1:8500 consul operator raft list-peers
    $ docker logs -f primary_consul_server_bootstrap_1
    ```
- Check `haproxy` logs
  ```
  $ docker logs -f haproxy
  ```

## Useful commands

* How to use set the correct VAULT_TOKEN

```
$ export VAULT_TOKEN=(cat tavern/${CLUSTER}/init.json | jq -r '.root_token')
```

* How to get the network IP of a container

```
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
- [x] Initialization and Unsealing with tavern
- [X] Configure Perfomance replication
- [X] Configure DR cluster
- [ ] Create replacement for Tavern
- [ ] Better startup handling
- [ ] Add Vault container for PKI
- [ ] Generate PKI certificates and use them
- [ ] Configure Monitoring
- [ ] HSM auto unsealing