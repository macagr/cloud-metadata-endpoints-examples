
import pulumi
import pulumi_azure_native.containerregistry as containerregistry
import pulumi_azure_native.containerinstance as containerinstance
import pulumi_azure_native.resources as resources
import pulumi_docker as docker
from pulumi_azure import core, keyvault, authorization, storage

resource_group = resources.ResourceGroup(
    "resourceGroup",
)

#Create simple blob to host our payload
storage_account = storage.Account("storageacc",
    resource_group_name=resource_group.name,
    location=resource_group.location,
    account_tier='Standard',
    account_replication_type="LRS",
    allow_blob_public_access=True)
storage_container = storage.Container("storagecont",
    storage_account_name = storage_account.name,
    container_access_type="blob")
payload_blob = storage.Blob("JavaCurl.jar",
    name="JavaCurl.jar",
    storage_account_name=storage_account.name,
    storage_container_name=storage_container.name,
    type="Block",
    source=pulumi.FileAsset("./java-curl/JavaCurl.jar"))


# Create test keyvault
client_config = core.get_client_config()
tenant_id = client_config.tenant_id
current_principal = client_config.object_id

vault = keyvault.KeyVault(
    "vault",
    resource_group_name=resource_group.name,
    sku_name="standard",
    tenant_id=tenant_id,
    access_policies=[keyvault.KeyVaultAccessPolicyArgs(
        tenant_id=tenant_id,
        object_id=current_principal,
        secret_permissions=["delete", "get", "list", "set"]
    )]
)

secret = keyvault.Secret(
    "deployment-zip",
    key_vault_id=vault.id,
    value="mySuperSecretValue")

secret_uri = pulumi.Output.all(vault.vault_uri, secret.name, secret.version) \
    .apply(lambda args: f"{args[0]}secrets/{args[1]}/{args[2]}")    


# Create user assigned identity
user_assigned_identity = authorization.UserAssignedIdentity("CGIdentity",
    resource_group_name = resource_group.name,
    location = resource_group.location)

# Key Vault Policy
policy = keyvault.AccessPolicy(
    "group-policy",
    key_vault_id = vault.id,
    tenant_id = tenant_id,
    object_id = user_assigned_identity.principal_id,
    secret_permissions=["get"])

# Deploying a custom image from Azure Container Registry.

custom_image = "youtrack-image"
registry = containerregistry.Registry(
    "registry",
    resource_group_name=resource_group.name,
    sku=containerregistry.SkuArgs(
        name="Basic",
    ),
    admin_user_enabled=True)

credentials = pulumi.Output.all(resource_group.name, registry.name).apply(
    lambda args: containerregistry.list_registry_credentials(resource_group_name=args[0],
                                                             registry_name=args[1]))
admin_username = credentials.username
admin_password = credentials.passwords[0]["value"]

my_image = docker.Image(
    custom_image,
    image_name=registry.login_server.apply(
        lambda login_server: f"{login_server}/{custom_image}:v1.0.0"),
    build=docker.DockerBuild(context=f"./{custom_image}"),
    registry=docker.ImageRegistry(
        server=registry.login_server,
        username=admin_username,
        password=admin_password
    )
)

# User assigned identities follow:
# /subscriptions/{subscriptionId}/resourceGroups/{resourceGroupName}/providers/Microsoft.ManagedIdentity/userAssignedIdentities/{identityName}’.

identity_qualifier = pulumi.Output.all(client_config.subscription_id, resource_group.name, user_assigned_identity.name).apply(
            lambda args: {f"/subscriptions/{args[0]}/resourceGroups/{args[1]}/providers/Microsoft.ManagedIdentity/UserAssignedIdentities/{args[2]}" : {}})

container_group = containerinstance.ContainerGroup("containerGroup",
    resource_group_name=resource_group.name,
    os_type="Linux",
    image_registry_credentials=[containerinstance.ImageRegistryCredentialArgs(server=registry.login_server.apply(lambda login_server: f"{login_server}"),
            username=admin_username,
            password=admin_password)],    
    containers=[containerinstance.ContainerArgs(
        name="acilinuxpublicipcontainergroup",
        image=my_image.image_name,
        ports=[containerinstance.ContainerPortArgs(port=8080)],
        resources=containerinstance.ResourceRequirementsArgs(
            requests=containerinstance.ResourceRequestsArgs(
                cpu=4.0,
                memory_in_gb=2.5,
            )
        ),
    )],
    ip_address=containerinstance.IpAddressArgs(
        ports=[containerinstance.PortArgs(
            port=8080,
            protocol="Tcp",
        )],
        type="Public",
    ),
    restart_policy="always",
    identity=containerinstance.ContainerGroupIdentityArgs(
        type="UserAssigned",
        user_assigned_identities = identity_qualifier, 
    )
)

pulumi.export("containerIPv4Address", container_group.ip_address.apply(lambda ip: ip.ip))
pulumi.export("blobURL", payload_blob.url)

