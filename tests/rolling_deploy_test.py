
import unittest
import License2Deploy.rolling_deploy 
import boto.ec2.autoscale as asg


class Test(unittest.TestCase):
    
    def test_return_min_ec2_count(self):
        desired_count = License2Deploy.rolling_deploy.return_autoscalinggroup_desired_size()
        self.assertEqual(5, desired_count)
    
    def test_retrieve_auto_scaling_group(self):
            """ AWS Call: retrieve the Auto Scaling Group by Tag """
    tag_name = "cloud"
    tag_value = "dev-cirrus-cache-microservice"
    asg_connection = asg.connect_to_region("us-east-1")
    all_tags = asg_connection.get_all_tags()
    auto_scaling_group_id = ""
    for tag in all_tags:
        if ((tag.key == tag_name) and (tag.value == tag_value)) :
            auto_scaling_group_id = tag.resource_id
    auto_scalling_group = asg_connection.get_all_groups(names=[auto_scaling_group_id])
    print "->", auto_scalling_group

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testDesiredEC2Count']
    unittest.main()