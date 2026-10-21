# CLI, infrastructure as code and troubleshooting

## CLI basics (read-only first)

```bash
ibmcloud login --sso                          # interactive user (or the organisation's login method)
ibmcloud login -r <region> -g <resource-group> # with IBMCLOUD_API_KEY set in the environment (automation)
ibmcloud login --cr-token @<token-file> --profile <trusted-profile-id>   # from a compute resource
ibmcloud target                               # confirm account, region, resource group before anything else
ibmcloud plugin list                          # installed plugins: container-service (ks), container-registry (cr), code-engine (ce), …

ibmcloud resource service-instances --type all
ibmcloud ks clusters; ibmcloud ks cluster get --cluster <name>
ibmcloud ks cluster config --cluster <name>    # kubeconfig (avoid --admin unless needed and agreed)
ibmcloud cr namespace-list; ibmcloud cr image-list --restrict <namespace>
ibmcloud ce project list; ibmcloud ce app get --name <app>; ibmcloud ce app events --name <app>; ibmcloud ce app logs --name <app>
```

Plugin names, aliases and flags change between versions: use `ibmcloud <plugin> --help` and the CLI reference. Never pass API keys on the command line (they end up in the shell history and process list): use the environment or `@file` with restricted permissions.

## Terraform and Schematics

```hcl
terraform {
  required_providers {
    ibm = { source = "IBM-Cloud/ibm", version = "~> 1.70" }   # pin to the version validated by the project
  }
}

provider "ibm" {
  region = var.region   # credentials from IBMCLOUD_API_KEY, never in code or tfvars committed to git
}
```

- Reuse the organisation's modules or `terraform-ibm-modules` (deployable architectures) rather than writing resources from scratch.
- Data sources (`data "ibm_resource_group"`, `data "ibm_is_vpc"`) to reference shared resources owned by other teams instead of duplicating them.
- State: Schematics workspaces manage the state and locking; for other backends, follow the organisation's standard (state contains secrets: encrypted, restricted access).
- Workflow: `terraform fmt -check`, `terraform validate`, `terraform plan -out=plan.tfplan`, a review of every `destroy`/`replace` (renaming a resource or changing an immutable argument recreates it; databases and buckets lose data), then apply through the pipeline or `ibmcloud schematics plan/apply --id <workspace>` when asked.
- Drift: a plan showing changes nobody made in code means someone used the console or CLI; bring the change into code or revert it deliberately.
- Protect critical resources with `lifecycle { prevent_destroy = true }` where the organisation agrees.

## Troubleshooting

| Symptom | Likely cause | Action |
| --- | --- | --- |
| `403` / "not authorized" | Missing IAM role at the right scope (platform vs service role), wrong resource group, **context-based restriction**, or the wrong account targeted | `ibmcloud target`; check the policies of the identity; check the CBR rules and their reports |
| Resource not found | Wrong region or resource group targeted | `ibmcloud target -r <region> -g <rg>` |
| Pods cannot pull from ICR | Pull secret missing in the namespace, private registry endpoint not reachable, image in another region | Copy or reference the ICR pull secret, check the registry endpoint and the namespace's region |
| App cannot reach Databases/COS privately | No VPE or private endpoint, security group or ACL blocking, DNS resolving to the public endpoint | Check the VPE, the security groups and the private endpoint hostname in the connection details |
| TLS errors connecting to Databases for PostgreSQL | Service CA certificate not trusted by the JVM | Add the CA from the connection details to the truststore (or the JDBC `sslrootcert`), never disable verification |
| Code Engine app not ready | Image pull, port mismatch (`--port`), failing startup, scale-to-zero cold start | `ibmcloud ce app events` and `logs`; align the port; set a minimum scale |
| Cluster ingress or Route not reachable | ALB or router disabled, DNS or certificate not provisioned, private-only cluster | Check the ingress status (`ibmcloud ks ingress status-report` or equivalent), certificates in Secrets Manager |
| Terraform wants to replace a resource unexpectedly | An immutable argument changed, a provider upgrade changed defaults, or a resource was renamed | Inspect the plan reason; use `moved {}` blocks for renames; pin the provider |
| Quota or limit errors | Account or regional limits | Report it; quota increases go through the account owners or support |
