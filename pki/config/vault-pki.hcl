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
  tls_disable  = "false"
  tls_cert_file = "/vault/ca/primary.pem"
  tls_key_file  = "/vault/ca/primary-key.pem"
}
ui = "true"
cluster_address = "0.0.0.0:8201"
cluster_name = "Primary"
# -----------------------------------------------------------------------
# Storage configuration
# -----------------------------------------------------------------------
storage "consul" {
  address            = "primary_consul_agent_1_1:8500"
  scheme             = "http"
#  tls_ca_file        = "/etc/ssl/certs/ca.pem"
  token = "49792521-8362-f878-5a32-7405f1783838"
  path               = "vault/"
# disable_clustering = "${disable_clustering}"
# service_tags       = "${service_tags}"
  service   	     = "pki"
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
  disable_hostname          = true
}