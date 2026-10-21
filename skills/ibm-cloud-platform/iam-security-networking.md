# IAM, security and networking

## IAM model

- **Account structure**: enterprise → account groups → accounts; inside an account, **resource groups** scope access and billing (often one per application and environment). Resources cannot move between resource groups after creation: choose the group deliberately.
- **People**: access groups (with dynamic rules from the corporate identity provider when federated), never individual policies.
- **Workloads**:
  - **Trusted profiles** for compute resources: a cluster, namespace and service account on IKS/ROKS, virtual servers, Code Engine. They give short-lived tokens without stored keys. Scope the compute resource as narrowly as possible (specific cluster, namespace and service account, not "all clusters").
  - **Service IDs** with API keys when no trusted-profile option fits (e.g. external CI runners): one per purpose, minimal policies, the key stored in the CI secret store or Secrets Manager, and rotated.
- **Roles**: platform roles (Viewer, Operator, Editor, Administrator) control the instance itself; service roles (Reader, Writer, Manager, plus service-specific ones) control data access. Grant the smallest pair on the narrowest scope (instance > resource group > account). Avoid policies on "All Identity and Access enabled services".
- Review access with `ibmcloud iam access-groups`, `ibmcloud iam access-group-policies <group>`, `ibmcloud iam service-policies <service-id>`, `ibmcloud iam trusted-profile-policies <profile>` (check `--help` for the installed CLI).

## Context-based restrictions (CBR)

CBR rules restrict access to services and resources to **network zones** (VPCs, IP ranges, other services) on top of IAM. Create new rules in **report-only** mode first, check the reports for legitimate traffic that would be blocked, then enforce. A `403` despite correct IAM policies is often a CBR rule.

## Networking (VPC)

- VPC with subnets per zone; **security groups** (stateful, per interface) as the main control, **network ACLs** (stateless, per subnet) as a coarse layer; a public gateway only for subnets that need outbound internet.
- **Private connectivity to IBM services** through private endpoints and **Virtual Private Endpoints (VPE)** (Databases, COS, Secrets Manager, Registry…); private-only clusters with private service endpoints; private load balancers for internal apps.
- Hybrid: Transit Gateway between VPCs, Direct Link or VPN to on-premises; DNS Services for private names.
- Document every new flow (source, destination, port, reason); default to deny.

## Compliance in regulated environments

- **Security and Compliance Center (SCC)** evaluates accounts against profiles (e.g. the IBM Cloud Framework for Financial Services, CIS benchmarks). Read the failing controls before changing resources; fix them in code.
- **IBM Cloud for Financial Services**: use validated services and the reference architecture (separate management and workload VPCs, private connectivity, customer-managed keys, bastion access); deviations need the organisation's risk approval.
- Data residency: deploy in the regions the organisation's policy allows, including backups, logs and replicas.
- Encryption: customer-managed keys (Key Protect/HPCS) on databases, COS, block storage and cluster secrets when required; TLS everywhere, including internal traffic if the policy says so.
