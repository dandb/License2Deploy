'''
Created on Sep 2, 2015

@author: thatchinamoorthyp
'''
import unittest
import License2Deploy.rolling_deploy 


class Test(unittest.TestCase):
    
    def test_return_min_ec2_count(self):
        desired_count = License2Deploy.rolling_deploy.return_autoscalinggroup_desired_size()
        self.assertEqual(5, desired_count)

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testDesiredEC2Count']
    unittest.main()