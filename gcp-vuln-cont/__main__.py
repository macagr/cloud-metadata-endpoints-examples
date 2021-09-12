"""A Google Cloud Python Pulumi program"""

import pulumi
import pulumi_gcp
from pulumi import Output, Config
from pulumi_gcp.cloudrun import (
    ServiceTemplateMetadataArgs,
    ServiceTemplateSpecContainerEnvArgs,
)
import pulumi_docker as docker

# Config stuff for getting docker to push things into gcr.io

config = Config()
config_file= config.require("docker-config-file")

image_name="vuln-youtrack"

gcr_docker_provider = docker.Provider("gcr",
	registry_auth=docker.provider.ProviderRegistryAuthArgs(
		address = "gcr.io",
		config_file = config_file)
	)

# Push image into gcr

image = docker.Image( image_name,
	image_name = Output.all().apply(lambda c: f"gcr.io/{pulumi_gcp.config.project}/{image_name}:latest"),
	build = docker.DockerBuild(context=f'./youtrack-image')
	)