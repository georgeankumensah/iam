provider "zitadel" {
  domain = var.zitadel_domain
  port   = "443"
  token  = var.zitadel_admin_token
}

provider "aws" {
  region = "eu-west-2"
}
