resource "zitadel_action_target" "complement_token" {
  org_id      = zitadel_org.main.id
  name        = "complement-token"
  target_type = "TARGET_TYPE_CALL"
  url         = "https://iam-api.clet.gov.gh/api/actions/complement-token"
  timeout     = "3s"
  payload_type = "PAYLOAD_TYPE_JSON"
  endpoint_type = "ENDPOINT_TYPE_REST"
  interrupt_on_error = true
  signing_key = var.zitadel_actions_signing_key
}

resource "zitadel_action_execution" "complement_token" {
  org_id       = zitadel_org.main.id
  includes     = ["urn:zitadel:iam:action:ComplementToken"]
  target       = zitadel_action_target.complement_token.id
  condition_type = "CONDITION_TYPE_POST_CONDITION"
}

resource "zitadel_action" "define_complement_token_flow" {
  org_id   = zitadel_org.main.id
  name     = "DefineComplementToken"
  script   = <<-EOT
    async function defineComplementToken(ctx, api) {
      api.registerTarget('complement-token', 'https://iam-api.clet.gov.gh/api/actions/complement-token');
    }
  EOT
  timeout  = "3s"
}

resource "zitadel_trigger_action" "complement_token_trigger" {
  org_id     = zitadel_org.main.id
  flow_type  = "FLOW_TYPE_EXTERNAL_AUTHENTICATION"
  trigger_type = "TRIGGER_TYPE_POST_AUTHENTICATION"
  action_ids = [zitadel_action.define_complement_token_flow.id]
}
