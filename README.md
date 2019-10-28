# What is it
A way to create a multiple Vault clusters and setup different types of Replication between them as close as possible to the "Vault reference architecture" https://learn.hashicorp.com/vault/operations/ops-reference-architecture

Using the 3 Region setup architecture:

![3 regions](https://d33wubrfki0l68.cloudfront.net/f4320f807477cdda5df25f904eaf3d7c9cfd761d/e6047/static/img/vault-ra-full-replication_no_region.png)

# Networks
It uses 3 networks:
* vault_primary
* vault_secondary
* vault_dr
  
Each network hosts this configuration of servers (currently only 3 Consul nodes):

![Single availability zone](https://d33wubrfki0l68.cloudfront.net/177ba67519ffb1c802f5cb699c0b70cb40533ab6/63838/static/img/vault-ra-1-az.png)

# Communication between them

It uses an (HAProxy) instance in TCP mode by accessing the IP trough DNS, this can be changed to any type of service discovery supported by Consul.

![proxy](https://d33wubrfki0l68.cloudfront.net/b2d787641bf2dda0a8a1abf691cd9723a9c0ed8c/7b419/static/img/vault-ref-arch-9.png)

# How
* Docker and docker-compose for the scheduling of containers.
* Docker-compose overlaying of configuration to avoid duplication
* [Tavern-ci](https://taverntesting.github.io/) for initialization and API management.
* Minimum use of simple shell scripts

# Why 
To be able to easily setup and test different configuration and features of a full fledge Vault and Consul cluster setup.

# Using it
On each directory, root, secondary and dr:
```
$ export CLUSTER=primary|secondary|dr
$ export VAULT_CLUSTER=${CLUSTER}
$ export CONSUL_CLUSTER=${CLUSTER}
$ export COMPOSE_PROJECT_NAME=${CLUSTER}
$ docker-compose -f docker-compose.${CLUSTER}.yml -f docker-compose.yml up -d
```
or

```
$ ./dc.sh up -d
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
- [ ] Add DR cluster
- [x] Add initialization with tavern
- [ ] Add vault container for PKI
- [ ] Generate PKI certificates and install them
