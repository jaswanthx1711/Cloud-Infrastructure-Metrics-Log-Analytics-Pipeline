###############################################################################
#  main.tf — Cloud Infrastructure Metrics & Log Analytics Pipeline (AWS)
#  Provisions the same infra as cloudformation.yaml via Terraform
###############################################################################

terraform {
  required_version = ">= 1.6"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
  # Uncomment to store state in S3:
  # backend "s3" {
  #   bucket = "my-terraform-state"
  #   key    = "cloud-metrics/terraform.tfstate"
  #   region = "eu-west-1"
  # }
}

provider "aws" {
  region = var.aws_region
  default_tags {
    tags = {
      Project     = var.project_name
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  }
}

# ── Variables ────────────────────────────────────────────────────────────
variable "aws_region"    { default = "eu-west-1" }
variable "project_name"  { default = "cloud-metrics" }
variable "environment"   { default = "dev" }
variable "account_id"    { default = "" }

locals {
  prefix     = "${var.project_name}-${var.environment}"
  account_id = var.account_id != "" ? var.account_id : data.aws_caller_identity.current.account_id
}

data "aws_caller_identity" "current" {}

# ── S3 — Data Lake ───────────────────────────────────────────────────────
resource "aws_s3_bucket" "datalake" {
  bucket = "${local.prefix}-datalake-${local.account_id}"
}

resource "aws_s3_bucket_versioning" "datalake" {
  bucket = aws_s3_bucket.datalake.id
  versioning_configuration { status = "Enabled" }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "datalake" {
  bucket = aws_s3_bucket.datalake.id
  rule {
    apply_server_side_encryption_by_default { sse_algorithm = "AES256" }
  }
}

resource "aws_s3_bucket" "scripts" {
  bucket = "${local.prefix}-scripts-${local.account_id}"
}

resource "aws_s3_bucket" "athena_results" {
  bucket = "${local.prefix}-athena-results-${local.account_id}"
}

resource "aws_s3_bucket_lifecycle_configuration" "athena_results" {
  bucket = aws_s3_bucket.athena_results.id
  rule {
    id     = "delete-old-results"
    status = "Enabled"
    expiration { days = 7 }
  }
}

# ── Upload Glue script to S3 ─────────────────────────────────────────────
resource "aws_s3_object" "glue_script" {
  bucket = aws_s3_bucket.scripts.id
  key    = "scripts/glue_job.py"
  source = "${path.module}/../glue_job.py"
  etag   = filemd5("${path.module}/../glue_job.py")
}

# ── IAM — Glue Role ──────────────────────────────────────────────────────
data "aws_iam_policy_document" "glue_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["glue.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "glue" {
  name               = "${local.prefix}-glue-role"
  assume_role_policy = data.aws_iam_policy_document.glue_assume.json
}

resource "aws_iam_role_policy_attachment" "glue_service" {
  role       = aws_iam_role.glue.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSGlueServiceRole"
}

resource "aws_iam_role_policy" "glue_s3" {
  name = "glue-s3-access"
  role = aws_iam_role.glue.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = ["s3:GetObject","s3:PutObject","s3:DeleteObject","s3:ListBucket"]
        Resource = [
          aws_s3_bucket.datalake.arn,
          "${aws_s3_bucket.datalake.arn}/*",
          aws_s3_bucket.scripts.arn,
          "${aws_s3_bucket.scripts.arn}/*",
        ]
      }
    ]
  })
}

# ── Glue Catalog Database ─────────────────────────────────────────────────
resource "aws_glue_catalog_database" "main" {
  name        = "${replace(var.project_name, "-", "_")}_${var.environment}"
  description = "Cloud Metrics Analytics — Bronze / Silver / Gold"
}

# ── Glue Crawlers ─────────────────────────────────────────────────────────
resource "aws_glue_crawler" "bronze" {
  name          = "${local.prefix}-bronze-crawler"
  role          = aws_iam_role.glue.arn
  database_name = aws_glue_catalog_database.main.name
  table_prefix  = "bronze_"

  s3_target {
    path = "s3://${aws_s3_bucket.datalake.id}/raw/"
  }

  schema_change_policy {
    update_behavior = "UPDATE_IN_DATABASE"
    delete_behavior = "LOG"
  }

  schedule = "cron(0 6 * * ? *)"
}

resource "aws_glue_crawler" "silver" {
  name          = "${local.prefix}-silver-crawler"
  role          = aws_iam_role.glue.arn
  database_name = aws_glue_catalog_database.main.name
  table_prefix  = "stg_"

  s3_target {
    path = "s3://${aws_s3_bucket.datalake.id}/silver/"
  }

  schema_change_policy {
    update_behavior = "UPDATE_IN_DATABASE"
    delete_behavior = "LOG"
  }
}

resource "aws_glue_crawler" "gold" {
  name          = "${local.prefix}-gold-crawler"
  role          = aws_iam_role.glue.arn
  database_name = aws_glue_catalog_database.main.name

  s3_target {
    path = "s3://${aws_s3_bucket.datalake.id}/gold/"
  }

  schema_change_policy {
    update_behavior = "UPDATE_IN_DATABASE"
    delete_behavior = "LOG"
  }
}

# ── Glue ETL Job ─────────────────────────────────────────────────────────
resource "aws_glue_job" "etl" {
  name              = "${local.prefix}-etl-job"
  role_arn          = aws_iam_role.glue.arn
  description       = "Cloud Metrics ETL — Bronze to Silver to Gold"
  glue_version      = "3.0"
  worker_type       = "G.1X"
  number_of_workers = 2
  timeout           = 60

  command {
    name            = "glueetl"
    script_location = "s3://${aws_s3_bucket.scripts.id}/scripts/glue_job.py"
    python_version  = "3"
  }

  default_arguments = {
    "--job-bookmark-option" = "job-bookmark-enable"
    "--enable-metrics"      = "true"
    "--S3_BUCKET"           = aws_s3_bucket.datalake.id
    "--DATABASE_NAME"       = aws_glue_catalog_database.main.name
    "--AWS_REGION"          = var.aws_region
  }
}

# ── Athena Workgroup ─────────────────────────────────────────────────────
resource "aws_athena_workgroup" "main" {
  name        = "${local.prefix}-workgroup"
  description = "Cloud Metrics analytics queries"

  configuration {
    result_configuration {
      output_location = "s3://${aws_s3_bucket.athena_results.id}/results/"
    }
    enforce_workgroup_configuration    = true
    publish_cloudwatch_metrics_enabled = true
    bytes_scanned_cutoff_per_query     = 10737418240  # 10 GB
  }
}

# ── Outputs ──────────────────────────────────────────────────────────────
output "datalake_bucket"      { value = aws_s3_bucket.datalake.id }
output "glue_database"        { value = aws_glue_catalog_database.main.name }
output "glue_job_name"        { value = aws_glue_job.etl.name }
output "athena_workgroup"     { value = aws_athena_workgroup.main.name }
output "athena_results_bucket"{ value = aws_s3_bucket.athena_results.id }
