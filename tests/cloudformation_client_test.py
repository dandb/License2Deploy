import os
import placebo
from boto3.session import Session
import unittest

from License2Deploy.rolling_deploy import RollingDeploy


class CloudformationClientTest(unittest.TestCase):

    def setUp(self):
        session = Session(region_name='us-west-1')
        current_dir = os.path.dirname(os.path.realpath(__file__))
        pill = placebo.attach(session, '{0}/test_data'.format(current_dir))
        pill.playback()
        self.rolling_deploy = RollingDeploy('stg', 'server-gms-extender', '0', 'ami-abcd1234', None, './regions.yml', stack_name='test-stack-name', session=session)

    def test_get_autoscaling_group_name_via_cloudformation(self):
        self.assertEqual(self.rolling_deploy.autoscaling_group, False)
        asg_name = self.rolling_deploy.get_autoscale_group_name()
        self.assertTrue(self.rolling_deploy.autoscaling_group)
        self.assertEqual(asg_name, 'dnbi-backend-qa-dnbigmsextenderASGqa-1NP5ZBSVZRD0N')
