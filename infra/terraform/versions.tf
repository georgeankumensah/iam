terraform {
  required_version = ">= 1.9"

  required_providers {
    zitadel = {
      source  = "zitadel/zitadel"
      version = "~> 2.11"
    }
  }

  backend "s3" {
    bucket = "clet-iam-terraform-state"
    key    = "zitadel/terraform.tfstate"
    region = "eu-west-2"
  }
}
