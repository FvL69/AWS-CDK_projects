import aws_cdk as core
import aws_cdk.assertions as assertions

from multi_tier_vpc.multi_tier_vpc_stack import MultiTierVpcStack

# example tests. To run these tests, uncomment this file along with the example
# resource in multi_tier_vpc/multi_tier_vpc_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = MultiTierVpcStack(app, "multi-tier-vpc")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
