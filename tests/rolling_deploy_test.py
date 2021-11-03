import sys
import pytest
import unittest
import boto
from boto.ec2.autoscale.launchconfig import LaunchConfiguration
from boto.ec2.autoscale.group import AutoScalingGroup
from boto.ec2.cloudwatch.alarm import MetricAlarm
from moto import mock_autoscaling_deprecated
from moto import mock_ec2_deprecated
from moto import mock_elb_deprecated
from moto.cloudwatch import mock_cloudwatch_deprecated

from License2Deploy.rolling_deploy import RollingDeploy
from License2Deploy.AWSConn import AWSConn


class RollingDeployTest(unittest.TestCase):

  autoscaling_group_name = 'autoscaling_group_name'
  launch_configuration_name = 'launch_configuration_name'
  load_balancer_name = 'load_balancer_name'

  GMS_LAUNCH_CONFIGURATION_STG = 'server-backend-stg-servergmsextenderLCstg-46TIE5ZFQTLB'
  GMS_LAUNCH_CONFIGURATION_PRD = 'server-backend-prd-servergmsextenderLCprd-46TIE5ZFQTLB'
  GMS_AUTOSCALING_GROUP_STG = 'server-backend-stg-servergmsextenderASGstg-3ELOD1FOTESTING'
  GMS_AUTOSCALING_GROUP_PRD = 'server-backend-prd-servergmsextenderASGprd-3ELOD1FOTESTING'

  @mock_autoscaling_deprecated
  @mock_elb_deprecated
  @mock_ec2_deprecated
  def setUp(self):
    self.setUpELB()
    self.rolling_deploy = RollingDeploy('stg', 'server-gms-extender', '0', 'ami-abcd1234', None, './regions.yml', force_redeploy=True)

  def get_autoscaling_configurations(self, launch_configuration_name, autoscaling_group_name):
    return {
      self.autoscaling_group_name: autoscaling_group_name,
      self.launch_configuration_name: launch_configuration_name
    }

  @mock_autoscaling_deprecated
  def setUpAutoScaleGroup(self, configurations, env="stg"):
    conn = boto.connect_autoscale()
    for configuration in configurations:
      config = LaunchConfiguration(
        name=configuration[self.launch_configuration_name],
        image_id='ami-abcd1234',
        instance_type='m1.medium',
      )
      load_balancer_name = self.load_balancer_name
      group = AutoScalingGroup(
        name=configuration[self.autoscaling_group_name],
        availability_zones=['us-east-1a'],
        default_cooldown=300,
        desired_capacity=2,
        health_check_period='0',
        health_check_type="EC2",
        max_size=10,
        min_size=2,
        launch_config=config,
        load_balancers=[load_balancer_name],
        vpc_zone_identifier='subnet-1234abcd',
        termination_policies=["Default"],
      )
      conn.create_launch_configuration(config)
      conn.create_auto_scaling_group(group)

  @mock_elb_deprecated
  def setUpELB(self, env='stg'):
    conn_elb = boto.connect_elb()
    zones = ['us-east-1a']
    ports = [(80, 8080, 'http')]
    load_balancer_name = self.load_balancer_name
    conn_elb.create_load_balancer(load_balancer_name, zones, ports)
    balancers = conn_elb.get_all_load_balancers(load_balancer_names=[load_balancer_name])
    self.assertEqual(balancers[0].name, load_balancer_name)

  @mock_ec2_deprecated
  @mock_elb_deprecated
  def setUpEC2(self, tag=True):
    self.setUpELB()
    conn_elb = boto.connect_elb()
    conn = boto.connect_ec2()
    instance_id_list = []
    reservation = conn.run_instances('ami-1234abcd', min_count=2, private_ip_address="10.10.10.10")
    instance_ids = reservation.instances
    for instance in instance_ids:
      if tag:
        instance.add_tag('BUILD', 0)
      instance_id_list.append(instance.id)
    elb = conn_elb.get_all_load_balancers(load_balancer_names=[self.load_balancer_name])[0]
    elb.register_instances(instance_id_list)
    elb_ids = [instance.id for instance in elb.instances]
    self.assertEqual(instance_id_list.sort(), elb_ids.sort())

    return [conn, instance_id_list]

  @mock_cloudwatch_deprecated
  def setUpCloudWatch(self, instance_ids, env="stg"):
    alarm = MetricAlarm(
      name = "servergmsextender_CloudWatchAlarm" + env,
      namespace = "AWS/EC2",
      metric = "CPUUtilization",
      comparison = ">=",
      threshold = "90",
      evaluation_periods = 1,
      statistic = "Average",
      period = 300,
      dimensions = {'InstanceId': instance_ids},
      alarm_actions=['arn:alarm'],
      ok_actions=['arn:ok']
    )
    watch_conn = boto.connect_cloudwatch()
    watch_conn.put_metric_alarm(alarm)

  @mock_cloudwatch_deprecated
  def setUpCloudWatchWithWrongConfig(self, instance_ids, env="stg"):
    alarm = MetricAlarm(
      name = "servergmsextender_CloudWatchAlarm" + env,
      namespace = "AWS/EC2",
      metric = "CPUUtilization",
      comparison = "GreaterThanThreshold", # wrong configuration that would generate error.
      threshold = "90",
      evaluation_periods = 1,
      statistic = "Average",
      period = 300,
      dimensions = {'InstanceId': instance_ids},
      alarm_actions=['arn:alarm'],
      ok_actions=['arn:ok']
    )
    watch_conn = boto.connect_cloudwatch()
    watch_conn.put_metric_alarm(alarm)

  @mock_ec2_deprecated
  def test_tag_ami(self):
    conn = self.setUpEC2()[0]
    reservation = conn.run_instances('ami-1234xyz1', min_count=1)
    instance_ids = reservation.instances
    conn.create_image(instance_ids[0].id, "test-ami", "this is a test ami")
    _ami_ids = conn.get_all_images()
    _ami_id = _ami_ids[0].id
    self.rolling_deploy = RollingDeploy('stg', 'server-gms-extender', '0', _ami_id, None, './regions.yml')
    self.rolling_deploy.tag_ami(str(_ami_id), 'stg')
    self.rolling_deploy.tag_ami(str(_ami_id), 'qa')
    self.rolling_deploy.tag_ami(str(_ami_id), 'qa')
    self.assertRaises(SystemExit, lambda: self.rolling_deploy.tag_ami('blargness', 'qa'))

  @mock_ec2_deprecated
  def test_load_config(self):
    self.assertEqual(AWSConn.load_config('regions.yml').get('qa'), 'us-west-1')
    self.assertEqual(AWSConn.load_config('regions.yml').get('stg'), 'us-east-1')
    self.assertEqual(AWSConn.load_config('regions.yml').get('prd'), 'us-east-1')
    self.assertEqual(AWSConn.load_config('regions.yml').get('default'), 'us-west-1')
    self.assertEqual(AWSConn.load_config('regions.yml').get('zero'), None)

  @mock_ec2_deprecated
  def test_load_config(self):
    self.assertEqual(AWSConn.determine_region('get-shwifty'), 'us-west-1')

  @mock_ec2_deprecated
  def test_wait_ami_availability(self):
    conn = self.setUpEC2()[0]
    inst_ids = self.setUpEC2()[1]
    conn.create_image(inst_ids[0], "test-ami", "this is a test ami")
    ami_ids = conn.get_all_images()
    ami_id = ami_ids[0]
    self.assertEqual(str(ami_id), str(self.rolling_deploy.get_ami_id_state(ami_id.id)))
    self.assertTrue(self.rolling_deploy.wait_ami_availability(ami_id.id))
    self.assertRaises(SystemExit, lambda: self.rolling_deploy.wait_ami_availability('bad-id')) #Will raise exception because ami can't be found
    self.assertRaises(SystemExit, lambda: self.rolling_deploy.wait_ami_availability(ami_id.id, -100)) #Will raise exception as time limit is over

  @mock_ec2_deprecated
  @mock_elb_deprecated
  def test_confirm_lb_has_only_new_instances(self):
    instance_ids = self.setUpEC2()[1]
    self.rolling_deploy.load_balancer = self.load_balancer_name
    self.assertEqual(len(instance_ids), len(self.rolling_deploy.confirm_lb_has_only_new_instances())) #Return All LB's with the proper build number

  @mock_ec2_deprecated
  @mock_elb_deprecated
  def test_lb_healthcheck(self):
    instance_ids = self.setUpEC2()[1]
    self.rolling_deploy.load_balancer = self.load_balancer_name
    self.assertTrue(self.rolling_deploy.lb_healthcheck(instance_ids)) #Return InService for all instances in ELB
    # Below doesn't work as I am unable to change the instance state. Need to modify elb_healthcheck method and also modify instance_health template.
    ## https://github.com/spulec/moto/blob/master/moto/elb/responses.py#L511 ##
    ## https://github.com/spulec/moto/blob/master/moto/elb/responses.py#L219 ##
    #self.assertRaises(SystemExit, lambda: self.rolling_deploy.lb_healthcheck(instance_ids, 1, 1)) #Return OutOfService for the first instance in the ELB which will raise an exit call

  @mock_autoscaling_deprecated
  def test_get_group_info(self):
    self.setUpAutoScaleGroup([self.get_autoscaling_configurations(self.GMS_LAUNCH_CONFIGURATION_STG, self.GMS_AUTOSCALING_GROUP_STG)])
    group = self.rolling_deploy.get_group_info([self.GMS_AUTOSCALING_GROUP_STG])[0]
    self.assertEqual(group.name, self.GMS_AUTOSCALING_GROUP_STG)

  @mock_autoscaling_deprecated
  def test_failure_get_group_info(self):
    self.setUpAutoScaleGroup([self.get_autoscaling_configurations(self.GMS_LAUNCH_CONFIGURATION_STG, self.GMS_AUTOSCALING_GROUP_STG)])
    self.assertRaises(SystemExit, lambda: self.rolling_deploy.get_group_info('cool'))

  @mock_autoscaling_deprecated
  def test_get_autoscale_group_name_stg(self):
    autoscaling_configurations = list()
    autoscaling_configurations.append(self.get_autoscaling_configurations(self.GMS_LAUNCH_CONFIGURATION_STG, self.GMS_AUTOSCALING_GROUP_STG))
    autoscaling_configurations.append(self.get_autoscaling_configurations(self.GMS_LAUNCH_CONFIGURATION_PRD, self.GMS_AUTOSCALING_GROUP_PRD))
    self.setUpAutoScaleGroup(autoscaling_configurations)
    group = self.rolling_deploy.get_autoscale_group_name()
    self.assertEqual(group, self.GMS_AUTOSCALING_GROUP_STG)
    self.assertNotEqual(group, self.GMS_AUTOSCALING_GROUP_PRD)

  @mock_autoscaling_deprecated
  @mock_elb_deprecated
  def test_get_autoscale_group_name_prd(self):
    self.setUpELB(env='prd')
    self.rolling_deploy = RollingDeploy('prd', 'server-gms-extender', '0', 'ami-test212', None, './regions.yml')
    autoscaling_configurations = list()
    autoscaling_configurations.append(self.get_autoscaling_configurations(self.GMS_LAUNCH_CONFIGURATION_PRD, self.GMS_AUTOSCALING_GROUP_PRD))
    self.setUpAutoScaleGroup(autoscaling_configurations, env='prd')
    group = self.rolling_deploy.get_autoscale_group_name()
    self.assertEqual(group, self.GMS_AUTOSCALING_GROUP_PRD)
    self.assertNotEqual(group, self.GMS_AUTOSCALING_GROUP_STG)

  @mock_autoscaling_deprecated
  def test_calculate_autoscale_desired_instance_count(self):
    self.setUpAutoScaleGroup([self.get_autoscaling_configurations(self.GMS_LAUNCH_CONFIGURATION_STG, self.GMS_AUTOSCALING_GROUP_STG)])
    increase = self.rolling_deploy.calculate_autoscale_desired_instance_count(self.GMS_AUTOSCALING_GROUP_STG, 'increase')
    decrease = self.rolling_deploy.calculate_autoscale_desired_instance_count(self.GMS_AUTOSCALING_GROUP_STG, 'decrease')
    self.assertEqual(increase, 4)
    self.assertEqual(decrease, 1)

  @mock_autoscaling_deprecated
  def test_calculate_autoscale_desired_instance_count_failure(self):
    self.setUpAutoScaleGroup([self.get_autoscaling_configurations(self.GMS_LAUNCH_CONFIGURATION_STG, self.GMS_AUTOSCALING_GROUP_STG)])
    self.assertRaises(SystemExit, lambda: self.rolling_deploy.calculate_autoscale_desired_instance_count(self.GMS_AUTOSCALING_GROUP_STG, 'nothing'))

  @mock_ec2_deprecated
  def test_get_instance_ip_addrs(self):
    self.setUpEC2()
    self.rolling_deploy.get_instance_ip_addrs(self.setUpEC2()[1])
    self.rolling_deploy.log_instances_ips(self.setUpEC2()[1], 'group')
    self.assertRaises(SystemExit, lambda: self.rolling_deploy.get_instance_ip_addrs(['blah', 'blarg']))

  @mock_ec2_deprecated
  def test_is_redeploy(self):
    self.setUpEC2()
    self.assertTrue(self.rolling_deploy.is_redeploy())

  @mock_ec2_deprecated
  def test_is_redeploy_fails(self):
    self.setUpEC2(tag=False)
    with pytest.raises(SystemExit):
      self.rolling_deploy.is_redeploy()

  def test_stop_deploy(self):
    with pytest.raises(SystemExit):
      self.rolling_deploy.stop_deploy('error!')

  @mock_ec2_deprecated
  @mock_autoscaling_deprecated
  @mock_elb_deprecated
  def test_get_all_instance_ids(self):
    self.setUpELB()
    self.setUpAutoScaleGroup([self.get_autoscaling_configurations(self.GMS_LAUNCH_CONFIGURATION_STG, self.GMS_AUTOSCALING_GROUP_STG)])
    conn = boto.connect_ec2()
    reservation = conn.run_instances('ami-1234abcd', min_count=2, private_ip_address="10.10.10.10")
    instance_ids = reservation.instances
    rslt = self.rolling_deploy.get_all_instance_ids(self.GMS_AUTOSCALING_GROUP_STG)
    self.assertEqual(len(instance_ids), len(rslt))

  @mock_ec2_deprecated
  @mock_autoscaling_deprecated
  @mock_elb_deprecated
  def test_validate_instance_list(self):
    self.setUpELB()
    self.setUpAutoScaleGroup([self.get_autoscaling_configurations(self.GMS_LAUNCH_CONFIGURATION_STG, self.GMS_AUTOSCALING_GROUP_STG)])
    conn = boto.connect_ec2()
    reservation = conn.run_instances('ami-1234abcd', min_count=2, private_ip_address="10.10.10.10")
    instances = reservation.instances
    self.assertTrue(self.rolling_deploy.validate_instance_list(instances))

  @mock_ec2_deprecated
  @mock_autoscaling_deprecated
  @mock_elb_deprecated
  def test_failure_validate_instance_list(self):
    instances = []
    self.assertRaises(Exception, lambda: self.rolling_deploy.validate_instance_list(instances))

  @mock_ec2_deprecated
  @mock_autoscaling_deprecated
  def test_get_instance_ids_by_requested_build_tag(self):
    self.setUpEC2()
    self.setUpAutoScaleGroup([self.get_autoscaling_configurations(self.GMS_LAUNCH_CONFIGURATION_STG, self.GMS_AUTOSCALING_GROUP_STG)])
    conn = boto.connect_ec2()
    new_inst = []
    res_ids = conn.get_all_instances()
    for i_id in res_ids:
       for name in i_id.instances:
         if [y for y in name.tags if y == 'BUILD' and name.tags['BUILD'] == '0']:
           new_inst.append(name.id)
    self.rolling_deploy.new_desired_capacity = self.rolling_deploy.calculate_autoscale_desired_instance_count(self.GMS_AUTOSCALING_GROUP_STG, 'increase')

    self.assertEqual(len(self.rolling_deploy.get_instance_ids_by_requested_build_tag(new_inst, 0)), 2)
    self.assertRaises(Exception, lambda: self.rolling_deploy.get_instance_ids_by_requested_build_tag(new_inst, 1))

    self.rolling_deploy.original_instance_ids = list(new_inst)
    self.rolling_deploy.force_redeploy = False
    self.assertEqual(len(self.rolling_deploy.get_instance_ids_by_requested_build_tag(new_inst, 0)), 2)
    self.rolling_deploy.force_redeploy = True
    self.assertRaises(Exception, lambda: self.rolling_deploy.get_instance_ids_by_requested_build_tag(new_inst, 0))

  @mock_ec2_deprecated
  @mock_autoscaling_deprecated
  def test_get_instance_ids_by_requested_build_tag_race_condition(self):
    self.setUpEC2()
    self.setUpAutoScaleGroup([self.get_autoscaling_configurations(self.GMS_LAUNCH_CONFIGURATION_STG, self.GMS_AUTOSCALING_GROUP_STG)])
    conn = boto.connect_ec2()
    new_inst = []
    res_ids = conn.get_all_instances()
    for i_id in res_ids:
       for name in i_id.instances:
         if [y for y in name.tags if y == 'BUILD' and name.tags['BUILD'] == '0']:
           new_inst.append(name.id)
           break
    self.rolling_deploy.force_redeploy = True
    self.rolling_deploy.new_desired_capacity = self.rolling_deploy.calculate_autoscale_desired_instance_count(self.GMS_AUTOSCALING_GROUP_STG, 'increase')
    self.assertRaises(Exception, lambda: self.rolling_deploy.get_instance_ids_by_requested_build_tag(new_inst, 1))


  @mock_ec2_deprecated
  def test_get_instance_ids_by_requested_build_tag_failure(self):
    self.setUpEC2()
    self.assertRaises(Exception, lambda: self.rolling_deploy.get_instance_ids_by_requested_build_tag([], 0))

  @mock_autoscaling_deprecated
  def test_set_autoscale_instance_desired_count(self):
    self.setUpAutoScaleGroup([self.get_autoscaling_configurations(self.GMS_LAUNCH_CONFIGURATION_STG, self.GMS_AUTOSCALING_GROUP_STG)])
    self.assertTrue(self.rolling_deploy.set_autoscale_instance_desired_count(4, self.GMS_AUTOSCALING_GROUP_STG))

  @mock_ec2_deprecated
  def test_wait_for_new_instances(self):
    instance_ids = self.setUpEC2()[1]
    self.assertEqual(self.rolling_deploy.wait_for_new_instances(instance_ids, 9), None)

  @mock_ec2_deprecated
  def test_wait_for_new_instances_failure(self):
    conn = self.setUpEC2()[0]
    instance_ids = self.setUpEC2()[1]
    reservations = conn.get_all_instances()
    reservations[0].instances[0].stop()
    self.assertRaises(SystemExit, lambda: self.rolling_deploy.wait_for_new_instances(instance_ids, 3, 1))

  def test_set_autoscale_instance_desired_count_failure(self):
    self.assertRaises(SystemExit, lambda: self.rolling_deploy.set_autoscale_instance_desired_count(4, self.GMS_AUTOSCALING_GROUP_STG))

  def test_double_autoscale_instance_count(self):
    self.assertEqual(self.rolling_deploy.double_autoscale_instance_count(2), 4)

  def test_decrease_autoscale_instance_count(self):
    self.assertEqual(self.rolling_deploy.decrease_autoscale_instance_count(4), 2)
