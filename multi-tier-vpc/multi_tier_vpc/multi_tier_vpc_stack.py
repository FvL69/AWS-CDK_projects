from aws_cdk import (
    # Duration,
    Stack,
    aws_ec2 as ec2,
    aws_rds as rds,
    # aws_elasticloadbalancingv2 as elbv2,
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
            # private subnet for future changes to the network architecture.
            subnet_configuration=[
                ec2.SubnetConfiguration(cidr_mask=25, name="Ingress", subnet_type=ec2.SubnetType.PUBLIC),
                ec2.SubnetConfiguration(cidr_mask=23, name="Application", subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
                ec2.SubnetConfiguration(cidr_mask=24, name="Database", subnet_type=ec2.SubnetType.PRIVATE_ISOLATED),
                ec2.SubnetConfiguration(cidr_mask=23, name="reserved", subnet_type=ec2.SubnetType.PRIVATE_ISOLATED, reserved=True),
            ]
        )

        # Security Group for app_instance1.
        self.SG_App1 = ec2.SecurityGroup(
            self, "AppSG1",
            vpc=self.vpc1,
            allow_all_outbound=True,
            description="Security Group for app_instance1"
        )


        # EC2 instance to host an application in ApplicationSubnet1.
        self.app_instance1 = ec2.Instance(
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
            #key_pair=
            security_group=self.SG_App1,
            #user_data=
        )


        # Security Group for app_instance2.
        self.SG_App2 = ec2.SecurityGroup(
            self, "AppSG2",
            vpc=self.vpc1,
            allow_all_outbound=True,
            description="Security Group for app_instance2"
        )

        # EC2 instance to host an application in ApplicationSubnet2.
        self.app_instance2 = ec2.Instance(
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
            #key_pair=,
            security_group=self.SG_App2,
            #user_data=,
        )


        # SG for db1.
        self.db_SG1 = ec2.SecurityGroup(
            self, "RDSdbSG1",
            vpc=self.vpc1,
            allow_all_outbound=True,
            description="Security Group for RDSdb1"
        )
        
        # db1
        self.db1 = rds.DatabaseInstance(
            self, "RDSdb1",
            engine=rds.DatabaseInstanceEngine.MYSQL,
            instance_type=ec2.InstanceType.of(ec2.InstanceClass.BURSTABLE3, ec2.InstanceSize.MICRO),
            vpc=self.vpc1,
            multi_az=True, # RDS will automatically create and manage a standby replica in a different AZ. 
            publicly_accessible=False,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_ISOLATED),
            security_groups=[self.db_SG1],
            allocated_storage=20,
            max_allocated_storage=20,
            delete_automated_backups=True,
            deletion_protection=False
        )
