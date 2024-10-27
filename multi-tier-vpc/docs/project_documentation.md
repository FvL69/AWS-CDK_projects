## Introduction:

In a multi-tier application architecture, you can introduce **extra layers of defense** between attackers and your sensitive resources. In this example, data is the most sensitive resource, so you would place it at the end of a chain to introduce two more layers of defense between attackers and your data.

In fact, you don't need to expose parts of your application in the public subnet at all if you use managed AWS endpoints, such as load balancers or Network Address Translation (NAT) options.  

Diagram link: [Multi-tier-architecture](../includes/diagram.png)  

#### Layer 1: Internet access resources. (public subnets)   
To limit exposure to the internet, you can use the following in your architecture:  
    1. An internet facing Application Load Balancer for incoming traffic.  
    2. A Nat solution (e.g. a NAT gateway or NAT instance) for outgoing traffic.  

#### Layer 2: Applications in a private subnet.    
This VPC also has a layer of private subnets for applications, running on EC2 instances. There are 512 IP addresses reserved in   each of these subnets to accommodate each application's need for scaling. It will also accommodate new applications as the   business's portfolio of applications expands.  

The Application Load Balancer attached to both public subnets distributes traffic between the application resources in the private subnets.  

#### Layer 3: Data in a second private subnet.  
This design puts data resources into a second private subnet behind the first private subnet. This example reserves fewer IP addresses than the application subnet but more IP addresses than the public subnet (you probably need to scale application resources than the data resources behind the application). 

The data layer can be a RDS deployment or a database running on an EC2. In either case, use a Multi-AZ configuration, as shown here. The secondary could be a read replica or a standby configured to automatically replace the primary should a failure occur. 

#### Extra IP addresses:
While you should always reserve more than enough IP addresses for your deployed infrastructure, it's also important to leave some of the extra IP addresses of your VPC available for changes to your network architecture. 

This architecture reserves 512 IP addresses in each private subnet. You can also just leave these IP addresses entirely unreserved, if you prefer but the subnet numbering will be altered when deploying these unreserved subnets/IP addresses.  

## Project constructs:

This project is build with **L2 constructs**, these are _curated constructs_ made by the AWS CDK team. Which entails that:  
L2 constructs include sensible default property configurations, best practice security policies, and generate a lot   
of the boilerplate code and glue logic for you.  

Which makes life easier if you don't posses advanced knowledge of AWS services to be able to build with L1 constructs yet.  
If you want to read more about this topic:  [AWS_CDK_Constructs](https://docs.aws.amazon.com/cdk/v2/guide/constructs.html)   

## Project steps:    

## 1. Create and configure the network: VPC, AZ's, Subnets and Gateways.   

### The Network.

    Create a VPC, constisting of:  
    1. 2 AZ's (Availability Zones)  
    2. 1 IGW (Internet gateway)
    3. 2 NGW's (NAT gateway, one for each public subnet)   
    4. 3 subnets (per AZ):    
        - 1 public. (for connecting to the internet)  
        - 1 private with egress. (for access to the internet through a NAT gateway)  
        - 1 private isolated. (isolated subnets do not route from or to the Internet)  
        - 1 reserved private isolated. (for future expansion of network and services)  

**note**: If you specialize the stack in the app.py file **for the AWS Account and Region that are implied by the current CLI configuration**, the max AZ's is 2 due to the fact that it's unknown in which region the app is going to be deployed. (there are regions with only 2 AZ's)  

ACL's, Routetables, SubnetRoutetableAssociations, logical routing (e.g, each Public Subnet will get a routetable with a route to the IGW), EIP's, Gateway attachments and a restricted default SG will be created by the L2 Vpc construct.   

## 2. Create and configure AWS resources: EC2 instances, RDSdb, ALB, listener, ASG and SG's.  

### The AWS resources.
 
    1. Create an EC2 Instance (Linux 2023 AMI) in each ApplicationSubnet.  

    2. Create a RDS db in DatabaseSubnet1.  
        - multi_az prop set to TRUE, RDS will automatically create and manage a synchronous replica in a different AZ.  
        - Remove the 'availability zones' property.
          Note: When you enable Multi-AZ, RDS automatically selects appropriate AZ's for the primary and standby instances  

    3. Create an ALB and attach it to the Public Subnets in both AZ's.  

## 3. Configure: SG rules, ACL rules and routing.

