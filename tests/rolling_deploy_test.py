#!/usr/bin/python

import unittest
import boto
import os
from boto.ec2.autoscale.launchconfig import LaunchConfiguration
from boto.ec2.autoscale.group import AutoScalingGroup
from moto import mock_autoscaling
from moto import mock_ec2
from moto import mock_elb
from License2Deploy.rolling_deploy import RollingDeploy
from License2Deploy.AWSConn import AWSConn

class RollingDeployTest(unittest.TestCase):

  @mock_autoscaling
  @mock_elb
  @mock_ec2
  def setUp(self):
    self.rolling_deploy = RollingDeploy('stg', 'server-gms-extender', '0', 'ami-abcd1234', None, './regions.yml')

  @mock_autoscaling
  def setUpAutoScaleGroup(self):
    conn = boto.connect_autoscale()
    config = LaunchConfiguration(
      name='server-backend-stg-servergmsextenderLCstg-46TIE5ZFQTLB',
      image_id='ami-abcd1234',
      instance_type='m1.medium',
    )
    group = AutoScalingGroup(
      name='server-backend-stg-servergmsextenderASGstg-3ELOD1FOTESTING',
      availability_zones=['us-east-1a'],
      default_cooldown=300,
      desired_capacity=2,
      health_check_period=0,
      health_check_type="EC2",
      max_size=10,
      min_size=2,
      launch_config=config,
      load_balancers=['servergmsextenderELBstg'],
      vpc_zone_identifier='subnet-1234abcd',
      termination_policies=["Default"],
    )

    conn.create_launch_configuration(config)
    conn.create_auto_scaling_group(group)

  @mock_elb
  def setUpELB(self):
    conn_elb = boto.connect_elb()
    zones = ['us-east-1a']
    ports = [(80, 8080, 'http')]
    conn_elb.create_load_balancer('servergmsextenderELBstg', zones, ports)
    balancers = conn_elb.get_all_load_balancers(load_balancer_names=['servergmsextenderELBstg'])
    self.assertEqual(balancers[0].name, 'servergmsextenderELBstg')

  @mock_ec2
  @mock_elb
  def setUpEC2(self):
    self.setUpELB()
    conn_elb = boto.connect_elb()
    conn = boto.connect_ec2()
    instance_id_list = []
    reservation = conn.run_instances('ami-1234abcd', min_count=2)
    instance_ids = reservation.instances
    for instance in instance_ids:
      instance.add_tag('BUILD', 0)
      instance_id_list.append(instance.id)
    elb = conn_elb.get_all_load_balancers(load_balancer_names=['servergmsextenderELBstg'])[0]
    elb.register_instances(instance_id_list)
    elb_ids = [instance.id for instance in elb.instances]
    self.assertEqual(instance_id_list.sort(), elb_ids.sort())

    return [conn, instance_id_list]

  @mock_ec2
  def test_load_config(self):
    self.assertEqual(AWSConn.load_config('regions.yml').get('qa'), 'us-west-1')
    self.assertEqual(AWSConn.load_config('regions.yml').get('stg'), 'us-east-1')
    self.assertEqual(AWSConn.load_config('regions.yml').get('prd'), 'us-east-1')
    self.assertEqual(AWSConn.load_config('regions.yml').get('default'), 'us-west-1')
    self.assertEqual(AWSConn.load_config('regions.yml').get('zero'), None)

  @mock_ec2
  def test_load_config(self):
    self.assertEqual(AWSConn.determine_region('get-shwifty'), 'us-west-1')

  @mock_ec2
  def test_wait_ami_availability(self): #NEED TO FINISH
    conn = self.setUpEC2()[0]
    inst_ids = self.setUpEC2()[1]
    conn.create_image(inst_ids[0], "test-ami", "this is a test ami")
    ami_ids = conn.get_all_images()
    ami_id = ami_ids[0]
    self.assertEqual(str(ami_id), str(self.rolling_deploy.get_ami_id_state(ami_id.id)))
    self.assertTrue(self.rolling_deploy.wait_ami_availability(ami_id.id))
    self.assertRaises(SystemExit, lambda: self.rolling_deploy.wait_ami_availability('bad-id')) #Will raise exception because ami can't be found

  @mock_ec2
  @mock_elb
  def test_confirm_lb_has_only_new_instances(self):
    instance_ids = self.setUpEC2()[1]
    self.assertEqual(len(instance_ids), len(self.rolling_deploy.confirm_lb_has_only_new_instances(1))) #Return All LB's with the proper build number

  @mock_elb
  def test_get_lb(self):
    self.setUpELB()
    self.assertEqual(u'servergmsextenderELBstg', self.rolling_deploy.get_lb()) #Return All LB's with the proper build number

  @mock_elb
  def test_get_lb_failure(self):
    self.setUpELB()
    self.rolling_deploy = RollingDeploy('stg', 'fake-server-gms-extender', '0', 'bad', 'server-deploy', './regions.yml') #Need for exception
    self.assertRaises(SystemExit, lambda: self.rolling_deploy.get_lb()) #Will raise exception because name can't be found

  @mock_ec2
  @mock_elb
  def test_lb_healthcheck(self):
    instance_ids = self.setUpEC2()[1]
    self.assertTrue(self.rolling_deploy.lb_healthcheck(instance_ids)) #Return InService for all instances in ELB
    # Below doesn't work as I am unable to change the instance state. Need to modify elb_healthcheck method and also modify instance_health template.
    ## https://github.com/spulec/moto/blob/master/moto/elb/responses.py#L511 ##
    ## https://github.com/spulec/moto/blob/master/moto/elb/responses.py#L219 ##
    #self.assertRaises(SystemExit, lambda: self.rolling_deploy.lb_healthcheck(instance_ids, 1, 1)) #Return OutOfService for the first instance in the ELB which will raise an exit call

  @mock_autoscaling
  def test_get_group_info(self):
    self.setUpAutoScaleGroup()
    group = self.rolling_deploy.get_group_info(['server-backend-stg-servergmsextenderASGstg-3ELOD1FOTESTING'])[0]
    self.assertEqual(group.name, 'server-backend-stg-servergmsextenderASGstg-3ELOD1FOTESTING')

  @mock_autoscaling
  def test_failure_get_group_info(self):
    self.setUpAutoScaleGroup()
    self.assertRaises(SystemExit, lambda: self.rolling_deploy.get_group_info('cool'))

  @mock_autoscaling
  def test_get_autoscale_group_name(self):
    self.setUpAutoScaleGroup()
    group = self.rolling_deploy.get_autoscale_group_name()
    self.assertEqual(group, 'server-backend-stg-servergmsextenderASGstg-3ELOD1FOTESTING')

  @mock_autoscaling
  def test_calculate_autoscale_desired_instance_count(self):
    self.setUpAutoScaleGroup()
    increase = self.rolling_deploy.calculate_autoscale_desired_instance_count('server-backend-stg-servergmsextenderASGstg-3ELOD1FOTESTING', 'increase')
    decrease = self.rolling_deploy.calculate_autoscale_desired_instance_count('server-backend-stg-servergmsextenderASGstg-3ELOD1FOTESTING', 'decrease')
    self.assertEqual(increase, 4)
    self.assertEqual(decrease, 1)

  @mock_autoscaling
  def test_calculate_autoscale_desired_instance_count_failure(self):
    self.setUpAutoScaleGroup()
    self.assertRaises(SystemExit, lambda: self.rolling_deploy.calculate_autoscale_desired_instance_count('server-backend-stg-servergmsextenderASGstg-3ELOD1FOTESTING', 'nothing'))

  @mock_autoscaling
  def test_get_all_instance_ids(self):
    self.setUpAutoScaleGroup()
    get_ids = len(self.rolling_deploy.get_all_instance_ids('server-backend-stg-servergmsextenderASGstg-3ELOD1FOTESTING'))
    self.assertEqual(get_ids, 2)

  @mock_ec2
  def test_get_instance_ids_by_requested_build_tag(self):
    self.setUpEC2()
    conn = boto.connect_ec2()
    new_inst = []
    res_ids = conn.get_all_instances()
    for i_id in res_ids:
       for name in i_id.instances:
         if [y for y in name.tags if y == 'BUILD' and name.tags['BUILD'] == '0']:
           new_inst.append(name.id)
    self.assertEqual(len(self.rolling_deploy.get_instance_ids_by_requested_build_tag(new_inst, 0)), 2)

  @mock_ec2
  def test_get_instance_ids_by_requested_build_tag_failure(self):
    self.setUpEC2()
    self.assertRaises(SystemExit, lambda: self.rolling_deploy.get_instance_ids_by_requested_build_tag([], 0))

  @mock_autoscaling
  def test_set_autoscale_instance_desired_count(self):
    self.setUpAutoScaleGroup()
    self.assertTrue(self.rolling_deploy.set_autoscale_instance_desired_count(4, 'server-backend-stg-servergmsextenderASGstg-3ELOD1FOTESTING'))

  @mock_ec2
  def test_wait_for_new_instances(self):
    instance_ids = self.setUpEC2()[1]
    self.assertEqual(self.rolling_deploy.wait_for_new_instances(instance_ids, 9), None)

  @mock_ec2
  def test_wait_for_new_instances_failure(self):
    conn = self.setUpEC2()[0]
    instance_ids = self.setUpEC2()[1]
    reservations = conn.get_all_instances()
    reservations[0].instances[0].stop()
    self.assertRaises(SystemExit, lambda: self.rolling_deploy.wait_for_new_instances(instance_ids, 3, 1))

  def test_set_autoscale_instance_desired_count_failure(self):
    self.assertRaises(SystemExit, lambda: self.rolling_deploy.set_autoscale_instance_desired_count(4, 'server-backend-stg-servergmsextenderASGstg-3ELOD1FOTESTING'))

  def test_double_autoscale_instance_count(self):
    self.assertEqual(self.rolling_deploy.double_autoscale_instance_count(2), 4)

  def test_decrease_autoscale_instance_count(self):
    self.assertEqual(self.rolling_deploy.decrease_autoscale_instance_count(4), 2)

def main():
    unittest.main()

if __name__ == "__main__":
    main()

