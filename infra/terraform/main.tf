resource "zitadel_org" "main" {
  name = var.org_name
}

resource "zitadel_domain" "primary" {
  org_id = zitadel_org.main.id
  domain = var.org_domain
}

resource "zitadel_project" "systems" {
  for_each = var.projects

  org_id          = zitadel_org.main.id
  name            = each.key
  project_role_check     = "PROJECT_ROLE_CHECK_NOT_REQUIRED"
  has_project_check      = false
  private_label_setting  = "PRIVATE_LABEL_SETTING_UNSPECIFIED"
}

resource "zitadel_project_role" "roles" {
  for_each = {
    for pair in flatten([
      for pk, p in var.projects : [
        for rk, r in p.roles : {
          id       = "${pk}/${rk}"
          project  = pk
          role_key = rk
          display  = r.display_name
          desc     = r.description
        }
      ]
    ]) : pair.id => pair
  }

  org_id       = zitadel_org.main.id
  project_id   = zitadel_project.systems[each.value.project].id
  role_key     = each.value.role_key
  display_name = each.value.display
  description  = each.value.desc
}

resource "zitadel_application_oidc" "apps" {
  for_each = var.oidc_applications

  org_id                   = zitadel_org.main.id
  project_id               = zitadel_project.systems[each.value.project_key].id
  name                     = each.value.display_name
  redirect_uris            = each.value.redirect_uris
  post_logout_redirect_uris = each.value.post_logout_uris
  additional_origins       = each.value.additional_origins
  access_token_type        = "ACCESS_TOKEN_TYPE_JWT"
  app_type                 = each.value.access_type == "CONFIDENTIAL" ? "OIDC_APP_TYPE_NATIVE" : "OIDC_APP_TYPE_USER_AGENT"
  auth_method_type         = each.value.access_type == "CONFIDENTIAL" ? "OIDC_AUTH_METHOD_TYPE_BASIC" : "OIDC_AUTH_METHOD_TYPE_NONE"
  version                  = "OIDC_VERSION_1_0"
  response_types           = ["OIDC_RESPONSE_TYPE_CODE"]
  grant_types              = ["OIDC_GRANT_TYPE_AUTHORIZATION_CODE"]
  dev_mode                 = false
  pkce_challenge_method    = each.value.pkce_challenge_method
}

resource "zitadel_org_member" "admins" {
  for_each = {
    for m in var.iam_admin_members : m.user_id => m
  }

  org_id  = zitadel_org.main.id
  user_id = each.value.user_id
  roles   = ["ORG_OWNER"]
}
