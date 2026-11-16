# AWS Configuration Template

Copy this to `~/.aws/config`:

```toml
[default]
sso_session = DevRev
sso_account_id = 020040093233
sso_role_name = EngineeringDevAccess
region = us-east-1

[sso-session DevRev]
sso_start_url = https://d-9067645937.awsapps.com/start
sso_region = us-east-1
sso_registration_scopes = sso:account:access

[profile dev]
sso_session = DevRev
sso_account_id = 020040093233
sso_role_name = EngineeringDevAccess
region = us-east-1

[profile dev-admin]
sso_session = DevRev
sso_account_id = 020040093233
sso_role_name = AdministratorAccess
region = us-east-1

[profile qa]
sso_session = DevRev
sso_account_id = 990737956189
sso_role_name = EngineeringQAAccess
region = us-east-1

[profile qa-admin]
sso_session = DevRev
sso_account_id = 990737956189
sso_role_name = AdministratorAccess
region = us-east-1

[profile prod-1]
sso_session = DevRev
sso_account_id = 087878894592
sso_role_name = EngineeringProdAccess
region = us-east-1

[profile prod-1-admin]
sso_session = DevRev
sso_account_id = 087878894592
sso_role_name = AdministratorAccess
region = us-east-1

[profile infraprod]
sso_session = DevRev
sso_account_id = 173672169127
# Note: typo in role name is intentional
sso_role_name = DeveloperInfraAcces
region = us-east-1
```

## Usage

```bash
# Login to dev
aws sso login --profile dev

# Verify identity
aws sts get-caller-identity --profile dev

# Use profile for commands
AWS_PROFILE=dev aws eks list-clusters
```
