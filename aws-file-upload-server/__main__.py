"""An AWS Python Pulumi program"""

import json
import base64
import pulumi
import pulumi_aws as aws
import pulumi_docker as docker

# The ECS cluster in which our service will run
app_cluster = aws.ecs.Cluster("upload-server-cluster")

# Creating a VPC and a public subnet
app_vpc = aws.ec2.Vpc("upload-server-vpc",
    cidr_block="172.31.0.0/16",
    enable_dns_hostnames=True)

app_vpc_subnet = aws.ec2.Subnet("upload-server-vpc-subnet",
    cidr_block="172.31.32.0/20",
    vpc_id=app_vpc.id)

# Creating a gateway to the web for the VPC and a route
app_gateway = aws.ec2.InternetGateway("upload-server-gateway",
    vpc_id=app_vpc.id)

app_routetable = aws.ec2.RouteTable("upload-server-routetable",
    routes=[
        aws.ec2.RouteTableRouteArgs(
            cidr_block="0.0.0.0/0",
            gateway_id=app_gateway.id,
        )
    ],
    vpc_id=app_vpc.id)

# Associating our gateway with our VPC, to allow our app to communicate with the greater internet
app_routetable_association = aws.ec2.MainRouteTableAssociation("upload-server_routetable_association",
    route_table_id=app_routetable.id,
    vpc_id=app_vpc.id)

# Creating a Security Group that restricts incoming traffic to HTTP
app_security_group = aws.ec2.SecurityGroup("security-group",
	vpc_id=app_vpc.id,
	description="Enables HTTP access",
    ingress=[aws.ec2.SecurityGroupIngressArgs(
		protocol='tcp',
		from_port=0,
		to_port=65535,
		cidr_blocks=['0.0.0.0/0'],
    )],
    egress=[aws.ec2.SecurityGroupEgressArgs(
		protocol='-1',
		from_port=0,
		to_port=0,
		cidr_blocks=['0.0.0.0/0'],
    )])

# Creating an IAM role used by Fargate to execute all our services
app_exec_role = aws.iam.Role("app-exec-role",
    assume_role_policy="""{
        "Version": "2012-10-17",
        "Statement": [
        {
            "Action": "sts:AssumeRole",
            "Principal": {
                "Service": "ecs-tasks.amazonaws.com"
            },
            "Effect": "Allow",
            "Sid": ""
        }]
    }""")

# Attaching execution permissions to the exec role
exec_policy_attachment = aws.iam.RolePolicyAttachment("app-exec-policy", role=app_exec_role.name,
	policy_arn="arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy")

# Creating an IAM role used by Fargate to manage tasks
app_task_role = aws.iam.Role("app-task-role",
    assume_role_policy="""{
        "Version": "2012-10-17",
        "Statement": [
        {
            "Action": "sts:AssumeRole",
            "Principal": {
                "Service": "ecs-tasks.amazonaws.com"
            },
            "Effect": "Allow",
            "Sid": ""
        }]
    }""")

# Creating an IAM role used by Fargate to manage tasks
ro_task_role = aws.iam.Role("ro-task-role",
    assume_role_policy="""{
        "Version": "2012-10-17",
        "Statement": [
        {
            "Action": "sts:AssumeRole",
            "Principal": {
                "Service": "ecs-tasks.amazonaws.com"
            },
            "Effect": "Allow",
            "Sid": ""
        }]
    }""")


# Attaching execution permissions to the task role
task_policy_attachment = aws.iam.RolePolicyAttachment("app-access-policy", role=app_task_role.name,
	policy_arn=aws.iam.ManagedPolicy.AMAZON_ECS_FULL_ACCESS)

# Creating repository to upload a docker image of our app to
app_ecr_repo = aws.ecr.Repository("app-ecr-repo",
    image_tag_mutability="MUTABLE")

# Attaching an application life cycle policy to the storage
app_lifecycle_policy = aws.ecr.LifecyclePolicy("app-lifecycle-policy",
    repository=app_ecr_repo.name,
    policy="""{
        "rules": [
            {
                "rulePriority": 10,
                "description": "Remove untagged images",
                "selection": {
                    "tagStatus": "untagged",
                    "countType": "imageCountMoreThan",
                    "countNumber": 1
                },
                "action": {
                    "type": "expire"
                }
            }
        ]
    }""")

#A youtrack service

# Creating a load balancer to spread out incoming requests
server_balancer = aws.lb.LoadBalancer("youtrack-balancer",
    load_balancer_type="network",
    internal=False,
    security_groups=[],
    subnets=[app_vpc_subnet.id])

# Creating a target group through which the youtrack receives requests
server_targetgroup = aws.lb.TargetGroup("youtrack-targetgroup",
    port=80,
    protocol="TCP",
    target_type="ip",
    stickiness=aws.lb.TargetGroupStickinessArgs(
        enabled=False,
        type="lb_cookie",
    ),
    vpc_id=app_vpc.id)

# Forwards all public traffic using port 80 to the youtrack target group
server_listener = aws.lb.Listener("youtrack-listener",
	load_balancer_arn=youtrack_balancer.arn,
	port=80,
    protocol="TCP",
	default_actions=[aws.lb.ListenerDefaultActionArgs(
		type="forward",
		target_group_arn=youtrack_targetgroup.arn
	)])

# Creating a Docker image from "./image/Dockerfile", which we will use
# to upload our app
def get_registry_info(rid):
    creds = aws.ecr.get_credentials(registry_id=rid)
    decoded = base64.b64decode(creds.authorization_token).decode()
    parts = decoded.split(':')
    if len(parts) != 2:
        raise Exception("Invalid credentials")
    return docker.ImageRegistry(creds.proxy_endpoint, parts[0], parts[1])

app_registry = app_ecr_repo.registry_id.apply(get_registry_info)

server_image = docker.Image("youtrack-dockerimage",
    image_name=app_ecr_repo.repository_url,
    build="./image",
    skip_push=False,
    registry=app_registry
)

# Creating a task definition for the youtrack instance.
server_task_definition = aws.ecs.TaskDefinition("youtrack-task-definition",
    family="youtrack-task-definition-family",
    network_mode="awsvpc",
    cpu="4096",
    memory="8192",
    requires_compatibilities=["FARGATE"],
    execution_role_arn=app_exec_role.arn,
    task_role_arn=app_task_role.arn,
    container_definitions=pulumi.Output.all(youtrack_image.image_name).apply(lambda args: json.dumps([{
        "name": "server-container",
        "image": args[0],
        "memory": 8192,
        "essential": True,
        "portMappings": [{
            "containerPort": 8080,
            "hostPort": 8080,
            "protocol": "tcp"
        }],
#        "environment": [ # Environment variables for the container
#            { "name": "GOT_SERVER", "value": args[1]["host"] },
#            { "name": "GOT_PORT", "value": str(args[1]["port"])},
#        ],
    }])))

# Launching App service on Fargate, using our configurations and load balancers
server_service = aws.ecs.Service("server-service",
	cluster=app_cluster.arn,
    desired_count=1,
    launch_type="FARGATE",
    enable_execute_command=True,
    task_definition=youtrack_task_definition.arn,
    wait_for_steady_state=False,
    network_configuration=aws.ecs.ServiceNetworkConfigurationArgs(
		assign_public_ip=True,
		subnets=[app_vpc_subnet.id],
		security_groups=[app_security_group.id]
	),
    load_balancers=[aws.ecs.ServiceLoadBalancerArgs(
		target_group_arn=youtrack_targetgroup.arn,
		container_name="server-container",
		container_port=8080,
	)],
    opts=pulumi.ResourceOptions(depends_on=[youtrack_listener]),
)


## Debugging role
# Create the role for the Lambda to assume
debug_role = aws.iam.Policy("debugPolicy", 
    description="debug policy",
    policy=json.dumps({
       "Version": "2012-10-17",
       "Statement": [
           {
           "Effect": "Allow",
           "Action": [
                "ssmmessages:CreateControlChannel",
                "ssmmessages:CreateDataChannel",
                "ssmmessages:OpenControlChannel",
                "ssmmessages:OpenDataChannel"
           ],
          "Resource": "*"
          }
       ]
       }
    )
)

# Attach the fullaccess policy to the debugging role created above. This is for executing inside the container
role_policy_attachment = aws.iam.RolePolicyAttachment("debugRoleAttachment",
    role=app_task_role.name,
    policy_arn=debug_role.arn)

# Exporting the url of our youtrack. We can now connect to our app
pulumi.export("app-url", server_balancer.dns_name)