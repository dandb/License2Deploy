import unittest
import boto.ec2.autoscale as asg
from _warnings import filters


class License2DeployTests(unittest.TestCase):

  def setUp(self):
      pass

  def test_retrieve_auto_scaling_group(self):
    """ AWS Call: retrieve the Auto Scaling Group by Tag """
    region = asg.connect_to_region("us-east-1")
    all_tags = region.get_all_tags()
    auto_scaling_group_id = ""
    for tag in all_tags:
        print vars(tag)
        if ((tag.key == "cloud") and (tag.value == "dev-cirrus-cache-microservice")) :
            auto_scaling_group_id = tag.resource_id
    
    print "auto scaling Group ID",  auto_scaling_group_id
    
def main():
    unittest.main()

if __name__ == "__main__":
    main()