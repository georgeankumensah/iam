# IAM 3.0 Terraform — Zitadel Bootstrap

Provisions Zitadel org, projects, OIDC apps, roles, login policies, and Actions V2 complement-token flow for CLET/GSL IAM 3.0.

## Prerequisites

- Terraform >= 1.9
- Zitadel instance running with admin PAT or service account token (`ZITADEL_ADMIN_TOKEN`)
- AWS credentials for S3 backend (or change backend to local)

## Usage

```bash
cp terraform.tfvars.example terraform.tfvars
# edit terraform.tfvars with real values

terraform init
terraform plan
terraform apply
```

## Structure

| File | Purpose |
|------|---------|
| `versions.tf` | Provider requirements, S3 state backend |
| `provider.tf` | Zitadel + AWS provider config |
| `variables.tf` | All input variables with defaults for 4 systems |
| `main.tf` | Org, domain, projects, roles, OIDC apps, admin members |
| `policies.tf` | Login policy (MFA mandatory), password/lockout/privacy policies |
| `actions.tf` | Actions V2 `complement-token` restCall target + execution |
| `outputs.tf` | Org ID, project IDs, application client IDs, action target ID |

## Post-Apply

After provisioning, configure the Django backend:

```bash
# Set the Actions V2 signing key matching the Terraform resource
export ZITADEL_ACTIONS_SIGNING_KEY="<same-key-from-terraform>"
```

Then run the Django drift checker to verify alignment:

```bash
python manage.py check_zitadel_drift
```

## Security

- `zitadel_admin_token` and `zitadel_actions_signing_key` are marked sensitive — never commit to VCS.
- Use `terraform.tfvars` locally only; for CI/CD, inject via environment variables or Vault.
- S3 backend should use KMS encryption and DynamoDB locking.
