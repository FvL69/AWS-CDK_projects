from aws_cdk import (
    Stack,
    aws_ec2 as ec2,
    aws_rds as rds,
    aws_elasticloadbalancingv2 as elbv2,
    aws_elasticloadbalancingv2_targets as elbv2_target,
    # aws_autoscaling as autoscaling,
    Duration,
    CfnTag,
    RemovalPolicy,
)
from constructs import Construct

class MultiTierVpcStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.vpc1 = ec2.Vpc(
            self, "Multi-tier_vpc",
            ip_addresses=ec2.IpAddresses.cidr("10.0.0.0/20"), # A /20 cidr gives 4096 ip addresses to work with.
            create_internet_gateway=True,
            enable_dns_hostnames=True,
            enable_dns_support=True,
            max_azs=2,
            nat_gateways=2,
            # Creating 3 subnets in each AZ as layers of defense to secure sensitive data, plus reserving an extra 
            # private subnet for future changes of the network architecture.
            subnet_configuration=[
                ec2.SubnetConfiguration(cidr_mask=25, name="Ingress", subnet_type=ec2.SubnetType.PUBLIC),
                ec2.SubnetConfiguration(cidr_mask=23, name="Application", subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
                ec2.SubnetConfiguration(cidr_mask=24, name="Database", subnet_type=ec2.SubnetType.PRIVATE_ISOLATED),
                ec2.SubnetConfiguration(cidr_mask=23, name="reserved", subnet_type=ec2.SubnetType.PRIVATE_ISOLATED, reserved=True),
            ]
        )

        
        ### SECURITY GROUPS ###

        # Security Group for Application Load Balancer.
        self.SG_ALB = ec2.SecurityGroup(
            self, "SG_ALB",
            vpc=self.vpc1,
            allow_all_outbound=True,
            description="Security Group for ALB",
        )

        # Security Group for AppInstance1.
        self.SG_App1 = ec2.SecurityGroup(
            self, "SG_App1",
            vpc=self.vpc1,
            allow_all_outbound=True,
            description="Security Group for AppInstance1"
        )

        # Security Group for AppInstance2.
        self.SG_App2 = ec2.SecurityGroup(
            self, "SG_App2",
            vpc=self.vpc1,
            allow_all_outbound=True,
            description="Security Group for AppInstance2"
        )

        # Security Group for RDSdb.
        self.SG_RDSdb = ec2.SecurityGroup(
            self, "SG_RDSdb",
            vpc=self.vpc1,
            allow_all_outbound=True,
            description="Security Group for RDSdb"
        )


        
        # EC2 instance to host an application in ApplicationSubnet1.
        self.AppInstance1 = ec2.Instance(
            self, "App-Instance1",
            instance_type=ec2.InstanceType("t2.micro"),
            machine_image=ec2.AmazonLinuxImage(generation=ec2.AmazonLinuxGeneration.AMAZON_LINUX_2023),
            vpc=self.vpc1,
            availability_zone=self.vpc1.availability_zones[0],
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
            block_devices=[ec2.BlockDevice(
                device_name="/dev/xvda", 
                volume=ec2.BlockDeviceVolume.ebs(
                    volume_size=30,
                    delete_on_termination=True,
                    iops=3000,
                    volume_type=ec2.EbsDeviceVolumeType.GP3,
                    )
                )
            ],
            security_group=self.SG_App1,
            user_data=None,
        )
            
        
        # EC2 instance to host an application in ApplicationSubnet2.
        self.AppInstance2 = ec2.Instance(
            self, "App-Instance2",
            instance_type=ec2.InstanceType("t2.micro"),
            machine_image=ec2.AmazonLinuxImage(generation=ec2.AmazonLinuxGeneration.AMAZON_LINUX_2023),
            vpc=self.vpc1,
            availability_zone=self.vpc1.availability_zones[1],
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
            block_devices=[ec2.BlockDevice(
                device_name="/dev/xvda",
                volume=ec2.BlockDeviceVolume.ebs(
                    volume_size=30,
                    delete_on_termination=True,
                    iops=3000,
                    volume_type=ec2.EbsDeviceVolumeType.GP3,
                    )
                )
            ],
            security_group=self.SG_App2,
            user_data=None,
        )
       

        # Application Load Balancer.
        self.alb = elbv2.ApplicationLoadBalancer(
            self, "ALB",
            vpc=self.vpc1,
            security_group=self.SG_ALB,
            internet_facing=True,
            ip_address_type=elbv2.IpAddressType.IPV4,
            idle_timeout=Duration.seconds(60),
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC),
            load_balancer_name="ALB",
            drop_invalid_header_fields=True,
        )

        # Target group.
        self.targetgroup = elbv2.ApplicationTargetGroup(
            self, "TargetGroup",
            vpc=self.vpc1,
            port=80,
            protocol=elbv2.ApplicationProtocol.HTTP,
            target_type=elbv2.TargetType.INSTANCE,
            target_group_name="TargetGroup",
            health_check=elbv2.HealthCheck(
                enabled=True,
                protocol=elbv2.Protocol.HTTP,
                healthy_http_codes="200",
                healthy_threshold_count=5,
                interval=Duration.seconds(30),
                path="/",
                timeout=Duration.seconds(6),
                unhealthy_threshold_count=2,
            ),
        )
        
        # Add targets to the target group.
        self.targetgroup.add_target(elbv2_target.InstanceTarget(self.AppInstance1))
        self.targetgroup.add_target(elbv2_target.InstanceTarget(self.AppInstance2))


        # HTTP listener.
        self.HTTP_listener = self.alb.add_listener(
            "HTTP_listener",
            port=80,
            open=True,
            default_action=elbv2.ListenerAction.forward([self.targetgroup])
        )

        
        
        # RDSdb 
        self.RDSdb = rds.DatabaseInstance(
            self, "RDSdb",
            engine=rds.DatabaseInstanceEngine.MYSQL,
            instance_type=ec2.InstanceType.of(ec2.InstanceClass.BURSTABLE3, ec2.InstanceSize.MICRO),
            vpc=self.vpc1,
            availability_zone=self.vpc1.availability_zones[0],
            multi_az=False, # If True: RDS will automatically create and manage a standby replica in a different AZ. 
            publicly_accessible=False,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_ISOLATED),
            security_groups=[self.SG_RDSdb],
            instance_identifier="MyRdsInstance",
            removal_policy=RemovalPolicy.DESTROY,
            storage_type=rds.StorageType.GP3,
            allocated_storage=20,
            max_allocated_storage=20,
            backup_retention=Duration.days(0),
            delete_automated_backups=True,
            deletion_protection=False
        )



        ### SECURITY GROUP RULES. ###

        # Application Load Balancer.
        # Ingress from internet.
        self.SG_ALB.add_ingress_rule(
            peer=ec2.Peer.ipv4("0.0.0.0/0"),
            connection=ec2.Port.tcp(80),
            description="Allow HTTP traffic",
        )

        # AppInstance1
        # Ingress rule for SSH from EIC Endpoint.
        self.SG_App1.add_ingress_rule(
            peer=self.SG_App1,
            connection=ec2.Port.tcp(22),
            description="Allow SSH traffic from EIC_Endpoint",
        )
        # Ingress rule for HTTP from ALB.
        self.SG_App1.add_ingress_rule(
            peer=self.SG_ALB,
            connection=ec2.Port.tcp(80),
            description="Allow HTTP traffic from SG_ALB",
        )
        # Ingress rule for RDSdb.
        self.SG_App1.add_ingress_rule(
            peer=self.SG_RDSdb,
            connection=ec2.Port.tcp(3306),
            description="Allow MySQL traffic from SG_RDSdb",
        )


        # AppInstance2.
        # Ingress rule for SSH from EIC Endpoint.
        self.SG_App2.add_ingress_rule(
            peer=self.SG_App2,
            connection=ec2.Port.tcp(22),
            description="Allow SSH traffic from EIC_Endpoint",
        )
        # Ingress rule for HTTP from ALB.
        self.SG_App2.add_ingress_rule(
            peer=self.SG_ALB,
            connection=ec2.Port.tcp(80),
            description="Allow HTTP traffic from SG_ALB",
        )
        # Ingress rule for RDSdb.
        self.SG_App2.add_ingress_rule(
            peer=self.SG_RDSdb,
            connection=ec2.Port.tcp(3306),
            description="Allow MySQL traffic from SG_RDSdb",
        )


        # RDS database.
        # Ingress rule for AppInstance1.
        self.SG_RDSdb.add_ingress_rule(
            peer=self.SG_App1,
            connection=ec2.Port.tcp(3306),
            description="Allow MySQL traffic from SG_App1",
        )
        # Ingress rule for AppInstance2.
        self.SG_RDSdb.add_ingress_rule(
            peer=self.SG_App2,
            connection=ec2.Port.tcp(3306),
            description="Allow MySQL traffic from SG_App2",
        )


        # SSH access for admin through EC2InstanceConnect Endpoint.
        self.EIC_Endpoint = ec2.CfnInstanceConnectEndpoint(
            self, "ec2InstanceConnectEndpoint",
            subnet_id=self.vpc1.select_subnets(
                availability_zones=[self.vpc1.availability_zones[0]],
                subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS,).subnets[0].subnet_id,
            security_group_ids=[self.SG_App1.security_group_id, self.SG_App2.security_group_id],
            tags=[CfnTag(key="Name", value="EIC_Endpoint")],
        )
        