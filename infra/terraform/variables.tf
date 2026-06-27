variable "zitadel_domain" {
  description = "Zitadel instance domain (e.g. iam.clet.gov.gh)"
  type        = string
}

variable "zitadel_admin_token" {
  description = "Zitadel PAT or service account token with IAM admin scope"
  type        = string
  sensitive   = true
}

variable "org_name" {
  description = "Zitadel organization name"
  type        = string
  default     = "CLET Ghana"
}

variable "org_domain" {
  description = "Primary domain for the org"
  type        = string
  default     = "clet.gov.gh"
}

variable "projects" {
  description = "Project definitions per system"
  type = map(object({
    display_name = string
    description  = string
    roles = map(object({
      display_name = string
      description  = string
    }))
  }))
  default = {
    gov = {
      display_name = "GOV Service"
      description  = "Government services portal"
      roles = {
        admin = {
          display_name = "Administrator"
          description  = "Full GOV admin access"
        }
        officer = {
          display_name = "Officer"
          description  = "Standard officer access"
        }
        viewer = {
          display_name = "Viewer"
          description  = "Read-only access"
        }
      }
    }
    ams = {
      display_name = "AMS"
      description  = "Application Management System"
      roles = {
        admin   = { display_name = "Admin", description = "Full AMS access" }
        manager = { display_name = "Manager", description = "Manage applications" }
        viewer  = { display_name = "Viewer", description = "View applications" }
      }
    }
    nbes = {
      display_name = "NBES"
      description  = "National Business Entry System"
      roles = {
        admin   = { display_name = "Admin", description = "Full NBES access" }
        officer = { display_name = "Officer", description = "Process entries" }
        viewer  = { display_name = "Viewer", description = "Read-only" }
      }
    }
    evs = {
      display_name = "EVS"
      description  = "Electronic Verification System"
      roles = {
        admin    = { display_name = "Admin", description = "Full EVS access" }
        verifier = { display_name = "Verifier", description = "Verify documents" }
        viewer   = { display_name = "Viewer", description = "Read-only" }
      }
    }
  }
}

variable "oidc_applications" {
  description = "OIDC client applications to create per project"
  type = map(object({
    project_key           = string
    display_name          = string
    access_type           = string
    redirect_uris         = list(string)
    post_logout_uris      = list(string)
    additional_origins    = optional(list(string), [])
    pkce_challenge_method = optional(string, "S256")
  }))
  default = {
    "console" = {
      project_key      = "gov"
      display_name     = "Admin Console"
      access_type      = "PKCE"
      redirect_uris    = ["https://console.clet.gov.gh/auth/callback"]
      post_logout_uris = ["https://console.clet.gov.gh/auth/logout"]
    }
    "ams-app" = {
      project_key           = "ams"
      display_name          = "AMS Frontend"
      access_type           = "PKCE"
      redirect_uris         = ["https://ams.clet.gov.gh/auth/callback"]
      post_logout_uris      = ["https://ams.clet.gov.gh/auth/logout"]
      additional_origins    = ["https://ams.clet.gov.gh"]
    }
    "nbes-app" = {
      project_key           = "nbes"
      display_name          = "NBES Frontend"
      access_type           = "PKCE"
      redirect_uris         = ["https://nbes.clet.gov.gh/auth/callback"]
      post_logout_uris      = ["https://nbes.clet.gov.gh/auth/logout"]
    }
    "evs-app" = {
      project_key           = "evs"
      display_name          = "EVS Frontend"
      access_type           = "PKCE"
      redirect_uris         = ["https://evs.clet.gov.gh/auth/callback"]
      post_logout_uris      = ["https://evs.clet.gov.gh/auth/logout"]
    }
    "iam-api" = {
      project_key           = "gov"
      display_name          = "IAM API (confidential)"
      access_type           = "CONFIDENTIAL"
      redirect_uris         = ["http://localhost:8000/auth/callback"]
      post_logout_uris      = ["http://localhost:8000/auth/logout"]
    }
    "admin-dashboard" = {
      project_key           = "gov"
      display_name          = "Admin Dashboard"
      access_type           = "PKCE"
      redirect_uris         = ["http://localhost:3001/auth/callback"]
      post_logout_uris      = ["http://localhost:3001/logout"]
      additional_origins    = ["http://localhost:3001"]
    }
  }
}

variable "zitadel_actions_signing_key" {
  description = "HMAC signing key for Actions V2 complement-token target"
  type        = string
  sensitive   = true
}

variable "iam_admin_members" {
  description = "Users to grant IAM_OWNER access to the org"
  type = list(object({
    user_id = string
  }))
  default = []
}
