
from License2Deploy.rolling_deploy import RollingDeploy
import License2Deploy.rolling_deploy 
from boto.ec2.autoscale import AutoScaleConnection
from boto.ec2.autoscale.group import AutoScalingGroup
from mock import MagicMock
from mock.mock import patch
import unittest

import boto.ec2.autoscale as asg


class Test(unittest.TestCase):
    
    def test_filter_auto_scaling_group(self):
        mock_autoscale_connection = MagicMock(spec=AutoScaleConnection)
        auto_scaling_groups = []
        auto_scaling_groups.append(AutoScalingGroup(name="dnbi-backend-stg-dnbibillingASGstg-1RYWS3F6LT9PW"))
        auto_scaling_groups.append(AutoScalingGroup(name="dnbi-backend-stg-dnbicacheASGstg-1O3HO09P2AHYJ"))
        auto_scaling_groups.append(AutoScalingGroup(name="dnbi-backend-stg-dnbicirrusASGstg-1GRJQVHPS4COJ"))
        auto_scaling_groups.append(AutoScalingGroup(name="dnbi-backend-stg-dnbiemailASGstg-1T3DV362TS505"))
        auto_scaling_groups.append(AutoScalingGroup(name="dnbi-backend-stg-dnbigmsextenderASGstg-62N1XQ4MRHSH"))
        mock_autoscale_connection.get_all_groups.return_value = auto_scaling_groups 
        
        rolling_deploy = RollingDeploy()
        rolling_deploy.aws_connection = mock_autoscale_connection
        
        desired_auto_scaling_group = rolling_deploy.retrieve_auto_scaling_group(app_name="dnbi", project_name="cache", environment="stg")
        self.assertEqual("dnbi-backend-stg-dnbicacheASGstg-1O3HO09P2AHYJ", desired_auto_scaling_group.name)
    
if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testDesiredEC2Count']
    unittest.main()