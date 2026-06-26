output "org_id" {
  description = "Zitadel organization ID"
  value       = zitadel_org.main.id
}

output "project_ids" {
  description = "Map of project key -> ID"
  value = {
    for k, p in zitadel_project.systems : k => p.id
  }
}

output "application_ids" {
  description = "Map of app key -> client_id"
  value = {
    for k, a in zitadel_application_oidc.apps : k => a.client_id
  }
}

output "actions_v2_target_id" {
  description = "Actions V2 complement-token target ID"
  value       = zitadel_action_target.complement_token.id
}
