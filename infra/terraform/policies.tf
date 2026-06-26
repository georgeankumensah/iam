resource "zitadel_login_policy" "org" {
  org_id = zitadel_org.main.id

  allow_register           = false
  allow_username_password  = true
  allow_external_idp      = false
  force_mfa               = true
  force_mfa_local_only    = false
  passwordless_type       = "PASSWORDLESS_TYPE_ALLOWED"
  ignore_unknown_usernames = true

  default_redirect_uri    = "https://console.clet.gov.gh/auth/callback"

  second_factors = [
    "SECOND_FACTOR_TYPE_OTP",
    "SECOND_FACTOR_TYPE_U2F",
  ]

  multi_factors = [
    "MULTI_FACTOR_TYPE_U2F_WITH_VERIFICATION",
  ]

  lifecycle {
    prevent_destroy = true
  }
}

resource "zitadel_password_complexity_policy" "org" {
  org_id = zitadel_org.main.id

  min_length    = 12
  has_uppercase = true
  has_lowercase = true
  has_number    = true
  has_symbol    = true
}

resource "zitadel_lockout_policy" "org" {
  org_id        = zitadel_org.main.id
  max_password_attempts = 5
  max_otp_attempts      = 3
}

resource "zitadel_privacy_policy" "org" {
  org_id    = zitadel_org.main.id
  tos_link  = "https://clet.gov.gh/terms"
  help_link = "https://clet.gov.gh/support"
}
