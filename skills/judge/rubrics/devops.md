# DevOps & Infrastructure Evaluation Rubric

## Overview
This rubric evaluates skills that manage infrastructure, deploy applications, configure CI/CD pipelines, containerize services, or automate operations. Use it for skills involving Docker, Kubernetes, Terraform, CI/CD configuration, server administration, and cloud infrastructure management.

## Dimension Criteria

### Correctness (Weight: 25%)
**What it measures in this domain:** Whether configurations are syntactically valid, deployments succeed, and infrastructure changes produce the expected state.

| Score | Criteria |
|-------|----------|
| 9-10  | All configurations are valid and functional. Deployments succeed. Infrastructure reaches desired state. No syntax or logic errors. |
| 7-8   | Configurations are mostly correct. Minor issues that do not prevent deployment or cause runtime failures. |
| 5-6   | Core configuration works but contains errors in secondary components. Some manual fixes needed post-deployment. |
| 3-4   | Multiple configuration errors. Deployment fails or produces incorrect state. Fundamental misunderstandings of tooling. |
| 1-2   | Configuration is invalid. Deployment completely fails. Infrastructure changes would cause outages. |

### Completeness (Weight: 20%)
**What it measures in this domain:** Whether all required infrastructure components, configurations, and operational concerns (monitoring, logging, backups) are addressed.

| Score | Criteria |
|-------|----------|
| 9-10  | All infrastructure components configured. Includes monitoring, logging, health checks, and rollback procedures. |
| 7-8   | Core infrastructure complete. Minor operational components (alerts, dashboards) may be missing. |
| 5-6   | Primary services configured but operational concerns (monitoring, backups) largely unaddressed. |
| 3-4   | Significant infrastructure components missing. No operational visibility or recovery procedures. |
| 1-2   | Only a fraction of required infrastructure configured. Incomplete to the point of being non-functional. |

### Adherence (Weight: 15%)
**What it measures in this domain:** Whether the output follows infrastructure-as-code best practices, naming conventions, and organizational standards.

| Score | Criteria |
|-------|----------|
| 9-10  | Follows all IaC best practices. Consistent naming. Proper use of variables, modules, and abstractions. |
| 7-8   | Generally follows conventions with minor deviations. Good use of parameterization. |
| 5-6   | Partially follows conventions. Some hardcoded values where variables should be used. |
| 3-4   | Significant deviation from best practices. Hardcoded secrets, no modularity, poor naming. |
| 1-2   | Ignores all conventions. Spaghetti configuration with no structure or standards. |

### Actionability (Weight: 15%)
**What it measures in this domain:** Whether the output can be directly applied (terraform apply, kubectl apply, docker-compose up) without modification.

| Score | Criteria |
|-------|----------|
| 9-10  | Ready to apply immediately. All prerequisites documented. Clear deployment instructions included. |
| 7-8   | Nearly ready to apply. Minor environment-specific values need updating. |
| 5-6   | Requires moderate customization before deployment. Missing some environment configuration. |
| 3-4   | Substantial rework needed. Missing critical configuration. Deployment steps unclear. |
| 1-2   | Not deployable. Would need to be rewritten from scratch. |

### Efficiency (Weight: 10%)
**What it measures in this domain:** Whether resources are appropriately sized, configurations are DRY, and unnecessary complexity is avoided.

| Score | Criteria |
|-------|----------|
| 9-10  | Optimal resource sizing. DRY configurations. No unnecessary services or over-engineering. |
| 7-8   | Mostly efficient. Minor over-provisioning or configuration duplication. |
| 5-6   | Some waste in resources or configuration. Noticeable duplication. |
| 3-4   | Significant over-provisioning or unnecessary complexity. Configuration is bloated. |
| 1-2   | Extremely wasteful. Resources grossly over-sized. Massive configuration duplication. |

### Safety (Weight: 10%)
**What it measures in this domain:** Whether secrets are properly managed, permissions follow least privilege, and destructive operations have safeguards.

| Score | Criteria |
|-------|----------|
| 9-10  | Secrets in vault/env vars. Least-privilege IAM. Network policies restrict access. Deletion protection enabled. |
| 7-8   | Good security posture. Minor improvements possible in permission scoping or network rules. |
| 5-6   | Basic security in place but some overly permissive rules or exposed ports. |
| 3-4   | Secrets in plaintext. Overly permissive IAM roles. No network segmentation. |
| 1-2   | Critical security failures. Root access, exposed credentials, no authentication, public database. |

### Consistency (Weight: 5%)
**What it measures in this domain:** Whether configurations maintain consistent patterns, naming, and quality across all resources and environments.

| Score | Criteria |
|-------|----------|
| 9-10  | Uniform patterns across all resources. Consistent naming, tagging, and configuration style. |
| 7-8   | Mostly consistent with minor naming or style variations. |
| 5-6   | Some inconsistency between resources or environments but generally followable. |
| 3-4   | Significant inconsistency. Different patterns used for similar resources. |
| 1-2   | No consistent patterns. Each resource configured in a completely different style. |

## Red Flags (Auto-Deductions)
- Secrets, passwords, or API keys hardcoded in configuration files
- Containers running as root without justification
- Overly permissive security groups (0.0.0.0/0 on sensitive ports)
- No resource limits on containers or pods
- Destructive operations without confirmation or rollback plan
- Missing health checks on services

## Domain-Specific Bonuses
- Includes rollback procedures and disaster recovery steps
- Implements blue-green or canary deployment strategies
- Provides cost estimates or optimization suggestions
- Includes comprehensive monitoring and alerting configuration
