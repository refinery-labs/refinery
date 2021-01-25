variable "root_account_id" {}

variable "access_key" {
}

variable "secret_key" {
}

variable "region" {
}

variable "s3_bucket_suffix" {
}

variable "assume_role_arn" {
}

variable "session_token" {
}

variable "role_session_name" {
}

variable "regional_amis" {
  type = map(string)

  /*
		Maps for the AMI ID of Ubuntu 18.04 in each AWS region.
	*/
  default = {
    us-east-1      = "ami-0a313d6098716f372"
    us-east-2      = "ami-0c55b159cbfafe1f0"
    us-west-1      = "ami-06397100adf427136"
    us-west-2      = "ami-005bdb005fb00e791"
    ca-central-1   = "ami-01b60a3259250381b"
    eu-central-1   = "ami-090f10efc254eaf55"
    eu-west-1      = "ami-08d658f84a6d84a80"
    eu-west-2      = "ami-07dc734dc14746eab"
    eu-west-3      = "ami-03bca18cb3dc173c9"
    eu-north-1     = "ami-5e9c1520"
    ap-northeast-1 = "ami-0eb48a19a8d81e20b"
    ap-northeast-2 = "ami-078e96948945fc2c9"
    ap-southeast-1 = "ami-0dad20bd1b9c8c004"
    ap-southeast-2 = "ami-0b76c3b150c6b1423"
    ap-south-1     = "ami-007d5db58754fa284"
    sa-east-1      = "ami-09f4cd7c0b533b081"
  }
}

variable "ssh_key_name" {
  default = "refinery-customer-support-ssh-key"
}

