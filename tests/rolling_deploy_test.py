
import License2Deploy.rolling_deploy 
from boto.ec2.autoscale.group import AutoScalingGroup
from boto.ec2.autoscale import AutoScaleConnection
from License2Deploy.rolling_deploy import RollingDeploy
import unittest
from mock import MagicMock

import boto.ec2.autoscale as asg


class Test(unittest.TestCase):
    
    def test_filter_auto_scaling_group(self):
        mock_autoscale_connection = AutoScaleConnection()
        auto_scaling_groups = []
        auto_scaling_groups.append(AutoScalingGroup(name="dnbi-backend-stg-dnbibillingASGstg-1RYWS3F6LT9PW"))
        auto_scaling_groups.append(AutoScalingGroup(name="dnbi-backend-stg-dnbicacheASGstg-1O3HO09P2AHYJ"))
        auto_scaling_groups.append(AutoScalingGroup(name="dnbi-backend-stg-dnbicirrusASGstg-1GRJQVHPS4COJ"))
        auto_scaling_groups.append(AutoScalingGroup(name="dnbi-backend-stg-dnbiemailASGstg-1T3DV362TS505"))
        auto_scaling_groups.append(AutoScalingGroup(name="dnbi-backend-stg-dnbigmsextenderASGstg-62N1XQ4MRHSH"))
        
        mock_autoscale_connection.get_all_groups = MagicMock(return_value=auto_scaling_groups) 
        asg.connect_to_region = MagicMock(return_value=mock_autoscale_connection)
        
        rolling_deploy = RollingDeploy()
        desired_auto_scaling_group = rolling_deploy.filter_auto_scaling_group(auto_scaling_groups, app_name="dnbi", project_name="email", environment="stg")
        
        self.assertEqual("dnbi-backend-stg-dnbiemailASGstg-1T3DV362TS505", desired_auto_scaling_group.name)
    
        
         
        
        

        
        
    
    

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testDesiredEC2Count']
    unittest.main()