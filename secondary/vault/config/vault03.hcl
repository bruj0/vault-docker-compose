# Vault OSS v1.2.3

# -----------------------------------------------------------------------
# Global configuration
# set via env variables
# -----------------------------------------------------------------------

# -----------------------------------------------------------------------
# Listener configuration
# -----------------------------------------------------------------------

listener "tcp" {
  address       = "0.0.0.0:8200"
  tls_disable  = "true"
#   #tls_cert_file = "/etc/ssl/certs/vault-server.crt"
#   #tls_key_file  = "/etc/ssl/vault-server.key"
}
ui = "true"
cluster_address = "0.0.0.0:8201"
cluster_name = "Secondary"
# -----------------------------------------------------------------------
# Storage configuration
# -----------------------------------------------------------------------
storage "consul" {
  address            = "secondary_consul_agent_1_1:8500"
  scheme             = "http"
#  tls_ca_file        = "/etc/ssl/certs/ca.pem"
  token = "50792521-8362-f878-5a32-7405f1783899"
  path               = "vault/"
# disable_clustering = "${disable_clustering}"
# service_tags       = "${service_tags}"
# service_address    = "vault01-service"
}

# -----------------------------------------------------------------------
# Optional cloud seal configuration
# -----------------------------------------------------------------------

# GCPKMS

# -----------------------------------------------------------------------
# Enable Prometheus metrics by default
# -----------------------------------------------------------------------

telemetry {
  prometheus_retention_time = "30s"
  disable_hostname          = false
}