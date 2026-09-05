#!/usr/bin/env python3
"""Upload/download one file to/from S3-compatible storage (e.g. DigitalOcean Spaces).

Intended to run inside the `web` container, which already has boto3 and sees the
repo at /app. Credentials and endpoint come from the environment:
  AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY  (required)
  AWS_S3_ENDPOINT_URL                        (required, e.g. https://<region>.digitaloceanspaces.com)
"""
import argparse
import os
import sys

import boto3


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["up", "down"])
    parser.add_argument(
        "--bucket",
        default=os.environ.get(
            "SPACES_BUCKET", os.environ.get("AWS_STORAGE_BUCKET_NAME", "sacred")
        ),
    )
    parser.add_argument("--key", required=True, help="Object key, e.g. archive/hall-latest.dump")
    parser.add_argument("--file", required=True, help="Local path (inside the container)")
    parser.add_argument(
        "--endpoint",
        default=os.environ.get("AWS_S3_ENDPOINT_URL"),
        help="S3-compatible endpoint URL (defaults to AWS_S3_ENDPOINT_URL)",
    )
    args = parser.parse_args()

    access_key = os.environ.get("AWS_ACCESS_KEY_ID")
    secret_key = os.environ.get("AWS_SECRET_ACCESS_KEY")
    if not access_key or not secret_key:
        sys.exit("ERROR: AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY are not set in the environment.")
    if not args.endpoint:
        sys.exit("ERROR: AWS_S3_ENDPOINT_URL is not set (pass --endpoint or set the env var).")

    s3 = boto3.client(
        "s3",
        endpoint_url=args.endpoint,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
    )

    if args.action == "up":
        s3.upload_file(args.file, args.bucket, args.key)
        print(f"uploaded {args.file} -> s3://{args.bucket}/{args.key}")
    else:
        s3.download_file(args.bucket, args.key, args.file)
        print(f"downloaded s3://{args.bucket}/{args.key} -> {args.file}")


if __name__ == "__main__":
    main()
