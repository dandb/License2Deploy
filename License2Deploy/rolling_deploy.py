#!/usr/bin/python

import logging
import argparse
from sys import exit, argv
from time import sleep, time
from AWSConn import AWSConn
from set_logging import SetLogging

class RollingDeploy(object):

  MAX_RETRIES = 10

  def __init__(self,
               env=None,
               project=None,
               build_number=None,
               ami_id=None,
               profile_name=None,
               regions_conf=None,
               stack_name=None,
               session=None):
    self.env = env
    self.session = session
    self.project = project.replace('-','')
    self.build_number = build_number
    self.ami_id = ami_id
    self.profile_name = profile_name
    self.regions_conf = regions_conf
    self.stack_name = stack_name
    self.stack_resources = False
    self.autoscaling_groups = False
    self.environments = AWSConn.load_config(self.regions_conf).get(self.env)
    self.region = AWSConn.determine_region(self.environments)
    self.conn_ec2 = AWSConn.aws_conn_ec2(self.region, self.profile_name)
    self.conn_elb = AWSConn.aws_conn_elb(self.region, self.profile_name)
    self.conn_auto = AWSConn.aws_conn_auto(self.region, self.profile_name)
    self.conn_cloudwatch = AWSConn.aws_conn_cloudwatch(self.region, self.profile_name)
    self.cloudformation_client = AWSConn.get_boto3_client('cloudformation', self.region, self.profile_name, session)
    self.exit_error_code = 2
    self.load_balancer = False

  def get_ami_id_state(self, ami_id):
    try:
      ami_obj = self.conn_ec2.get_all_images(image_ids=ami_id)
    except Exception as e:
      logging.error("Unable to get ami-id, please investigate: {0}".format(e))
      exit(self.exit_error_code)
    return ami_obj[0]

  def wait_ami_availability(self, ami_id, timer=20):
    ''' Timeout should be in minutes '''
    timeout = time() + 60 * timer
    while True:
      ami_state = self.get_ami_id_state(ami_id).state
      if time() <= timeout and ami_state == 'available':
        logging.info("AMI {0} is ready".format(ami_id))
        return True
      elif time() > timeout:
        logging.error("AMI {0} is not ready after {1} minutes, please investigate".format(ami_id, timer))
        exit(self.exit_error_code)
      else:
        logging.warning("AMI {0} is not ready yet, retrying in 30 seconds".format(ami_id))
        sleep(30)

  def get_group_info(self, group_name=None):
    try:
      if group_name:
        rslt = self.conn_auto.get_all_groups([group_name])
        if not rslt:
          raise Exception("Bad Group: {0}".format(group_name))
        return rslt
      else:
        return self.conn_auto.get_all_groups()
    except Exception as e:
      logging.error("Unable to pull down autoscale group: {0}".format(e))
      exit(self.exit_error_code)

  def get_autoscale_group_name(self):
    ''' Search for project in autoscale groups and return autoscale group name '''
    if self.stack_name:
      return self.get_autoscaling_group_name_from_cloudformation()
    return next((instance.name for instance in filter(lambda n: n.name, self.get_group_info()) if self.project in instance.name and self.env in instance.name), None)

  def get_autoscaling_group_name_from_cloudformation(self):
    if not self.autoscaling_groups:
      self.autoscaling_groups = [asg for asg in self.get_stack_resources() if asg['ResourceType'] == 'AWS::AutoScaling::AutoScalingGroup']
    return [asg['PhysicalResourceId'] for asg in self.autoscaling_groups if self.project in asg['PhysicalResourceId']][0]

  def get_stack_resources(self):
    if not self.stack_resources:
      self.stack_resources = self.cloudformation_client.list_stack_resources(StackName=self.stack_name)['StackResourceSummaries']
    return self.stack_resources

  def get_lb(self):
    try:
      return next(n.name for n in self.conn_elb.get_all_load_balancers() if self.project in str(n.name) and self.env in str(n.name))
    except Exception as e:
      logging.error("Unable to pull down ELB info: {0}".format(e))
      exit(self.exit_error_code)

  def calculate_autoscale_desired_instance_count(self, group_name, desired_state):
    ''' Search via specific autoscale group name to return modified desired instance count '''
    try:
      cur_count = int(self.get_group_info(group_name)[0].desired_capacity)
      if desired_state == 'increase':
        new_count = self.double_autoscale_instance_count(cur_count)
      elif desired_state == 'decrease':
        new_count = self.decrease_autoscale_instance_count(cur_count)
      logging.info("Current desired count was changed from {0} to {1}".format(cur_count, new_count))
      return new_count
    except Exception as e:
      logging.error("Please make sure the desired_state is set to either increase or decrease: {0}".format(e))
      exit(self.exit_error_code)
 
  def double_autoscale_instance_count(self, count):
    ''' Multiply current count by 2 '''
    return count * 2

  def decrease_autoscale_instance_count(self, count):
    ''' Divide current count in half '''
    return count / 2

  def set_autoscale_instance_desired_count(self, new_count, group_name):
    ''' Increase desired count by double '''
    try:
      logging.info("Set autoscale capacity for {0} to {1}".format(group_name, new_count))
      self.conn_auto.set_desired_capacity(group_name, new_count)
      return True
    except Exception as e:
      logging.error("Unable to update desired count, please investigate error: {0}".format(e))
      exit(self.exit_error_code)

  def get_instance_ip_addrs(self, id_list=[]):
    ip_dict = {}
    try:
      instance_data = [ids for instInfo in self.conn_ec2.get_all_instances(instance_ids=id_list) for ids in instInfo.instances]
      for instance in instance_data:
        ip_dict[instance.id] = instance.private_ip_address
      return ip_dict
    except Exception as e:
      logging.error("Unable to get IP Addresses for instances: {0}".format(e))
      exit(self.exit_error_code)

  def get_all_instance_ids(self, group_name):
    ''' Gather Instance id's of all instances in the autoscale group '''
    instances = [i for i in self.get_group_info(group_name)[0].instances]
    id_list = [instance_id.instance_id for instance_id in instances]
    id_ip_dict = self.get_instance_ip_addrs(id_list)

    logging.info("List of all Instance ID's and IP addresses in {0}: {1}".format(group_name, id_ip_dict))
    return id_list

  def get_instance_ids_by_requested_build_tag(self, id_list, build):
    ''' Gather Instance id's of all instances in the autoscale group '''
    reservations = self.conn_ec2.get_all_reservations(instance_ids=id_list)
    new_instances = []
    for instance_id in id_list:
      instances_build_tags = [inst for r in reservations for inst in r.instances if 'BUILD' in inst.tags and inst.id == instance_id]
      new_instances += [instance_id for new_id in instances_build_tags if new_id.tags['BUILD'] == str(build)]

    if not new_instances:
      logging.error("There are no instances in the group with build number {0}. Please ensure AMI was promoted.\nInstance ID List: {1}".format(build, id_list))
      group_name = self.get_autoscale_group_name()
      self.set_autoscale_instance_desired_count(self.calculate_autoscale_desired_instance_count(group_name, 'decrease'), group_name)
      exit(self.exit_error_code)

    id_ip_dict = self.get_instance_ip_addrs(new_instances)
    logging.info("New Instance List with IP Addresses: {0}".format(id_ip_dict))
    return new_instances

  def wait_for_new_instances(self, instance_ids, retry=10, wait_time=30):
    ''' Monitor new instances that come up and wait until they are ready '''
    for instance in instance_ids:
      count = 0
      health = []
      while count <= retry and (len(health) < 2):
        instanceStatus = self.conn_ec2.get_all_instance_status(instance)
        for state in instanceStatus:
          health = [x for x in [str(state.system_status.status), str(state.instance_status.status)] if x == "ok"]
          if (len(health) < 2):
            logging.warning("{0} is not in a fully working state yet".format(instance))
            sleep(wait_time)
            count += 1
            if count > retry:
              logging.error("{0} has not reached a valid healthy state".format(instance))
              self.revert_deployment()
          else:
            logging.info("{0} is in a healthy state. Moving on...".format(instance))

  def lb_healthcheck(self, new_ids, attempt=0, wait_time=0):
    ''' Confirm that the healthchecks report back OK in the LB. '''
    try:
      attempt += 1
      if attempt > self.MAX_RETRIES:
        logging.error('Load balancer healthcheck has exceeded the timeout threshold. Rolling back.')
        self.revert_deployment()
      sleep(wait_time)
      instance_ids = self.conn_elb.describe_instance_health(self.load_balancer, new_ids)
      status = filter(lambda instance: instance.state != "InService", instance_ids)
      if status:
        logging.info('Must check load balancer again. Following instance(s) are not "InService": {0}'.format(status))
        return self.lb_healthcheck(new_ids, attempt=attempt, wait_time=30)
    except Exception as e:
      logging.error('Failed to health check load balancer instance states. Error: {0}'.format(e))
      self.revert_deployment()
    logging.info('ELB healthcheck OK')
    return True

  def confirm_lb_has_only_new_instances(self, wait_time=60):
    ''' Confirm that only new instances with the current build tag are in the load balancer '''
    sleep(wait_time) # Allotting time for the instances to shut down
    instance_ids = self.conn_elb.describe_instance_health(self.load_balancer)
    for instance in instance_ids:
      build = self.conn_ec2.get_all_reservations(instance.instance_id)[0].instances[0].tags['BUILD']
      if build != self.build_number:
        logging.error("There is still an old instance in the ELB: {0}. Please investigate".format(instance))
        exit(self.exit_error_code)
    logging.info("Deployed instances {0} to ELB: {1}".format(instance_ids, self.load_balancer))
    return instance_ids

  def tag_ami(self, ami_id, env):
    ''' Tagging AMI with DEPLOYED tag '''
    try:
      current_tag = self.conn_ec2.get_all_images(image_ids=ami_id)[0].tags.get('deployed')
      if not current_tag: 
        logging.info("No DEPLOY tags exist, tagging with {0}".format(env))
        self.conn_ec2.create_tags([self.ami_id], {"deployed": env})
      elif env not in current_tag:
        new_tag = ', '.join([current_tag, env])
        logging.info("DEPLOY tags currently exist: {0}, new tag is {1}".format(current_tag, new_tag))
        self.conn_ec2.create_tags([self.ami_id], {"deployed": new_tag})
      else:
        logging.info("No tagging necessary, already tagged with env: {0}".format(env))
    except Exception as e:
      logging.error("Unable to tag ID, please investigate: {0}".format(e))
      exit(self.exit_error_code)

  def gather_instance_info(self, group): #pragma: no cover
    instance_ids = self.get_all_instance_ids(group)
    new_instance_ids = self.get_instance_ids_by_requested_build_tag(instance_ids, self.build_number)
    return new_instance_ids

  def healthcheck_new_instances(self, group_name): # pragma: no cover
    ''' Healthchecking new instances to ensure deployment was successful '''
    new_instance_ids = self.gather_instance_info(group_name)
    self.wait_for_new_instances(new_instance_ids) #Wait for new instances to be up and ready
    self.lb_healthcheck(new_instance_ids) #Once instances are ready, healthcheck. If successful, decrease desired count.

  def retrieve_project_cloudwatch_alarms(self):
    """ Retrieve all the Cloud-Watch alarms for the given project and environment """
    try:
      all_cloud_watch_alarms = self.conn_cloudwatch.describe_alarms()
    except Exception as e:
      logging.error("Error while retrieving the list of cloud-watch alarms. Error: {0}".format(e))
      exit(self.exit_error_code)
    project_cloud_watch_alarms = filter(lambda alarm: self.project in alarm.name and self.env in alarm.name, all_cloud_watch_alarms)
    if len(project_cloud_watch_alarms) == 0:
       logging.info("No cloud-watch alarm found")
    return project_cloud_watch_alarms

  def disable_project_cloudwatch_alarms(self):
    ''' Disable all the cloud watch alarms '''
    project_cloud_watch_alarms = self.retrieve_project_cloudwatch_alarms()
    for alarm in project_cloud_watch_alarms:
      try:
        self.conn_cloudwatch.disable_alarm_actions(alarm.name)
        logging.info("Disabled cloud-watch alarm. {0}".format(alarm.name))
      except Exception as e:
        logging.error("Unable to disable the cloud-watch alarm, please investigate: {0}".format(e))
        exit(self.exit_error_code)

  def enable_project_cloudwatch_alarms(self):
    ''' Enable all the cloud watch alarms '''
    project_cloud_watch_alarms = self.retrieve_project_cloudwatch_alarms()
    for alarm in project_cloud_watch_alarms:
      logging.info("Found an alarm. {0}".format(alarm.name))
      try:
        self.conn_cloudwatch.enable_alarm_actions(alarm.name)
        logging.info("Enabled cloud-watch alarm. {0}".format(alarm.name))
      except Exception as e:
        logging.error("Unable to enable the cloud-watch alarm, please investigate: {0}".format(e))
        exit(self.exit_error_code)

  def deploy(self): # pragma: no cover
    self.load_balancer = self.get_lb()
    ''' Rollin Rollin Rollin, Rawhide! '''
    group_name = self.get_autoscale_group_name()
    self.wait_ami_availability(self.ami_id)
    logging.info("Build #: {0} ::: Autoscale Group: {1}".format(self.build_number, group_name))
    self.disable_project_cloudwatch_alarms()
    self.set_autoscale_instance_desired_count(self.calculate_autoscale_desired_instance_count(group_name, 'increase'), group_name)
    logging.info("Sleeping for 240 seconds to allow for instances to spin up")
    sleep(240) #Need to wait until the instances come up in the load balancer
    self.healthcheck_new_instances(group_name)
    self.set_autoscale_instance_desired_count(self.calculate_autoscale_desired_instance_count(group_name, 'decrease'), group_name)
    self.confirm_lb_has_only_new_instances()
    self.tag_ami(self.ami_id, self.env)
    self.enable_project_cloudwatch_alarms()
    logging.info("Deployment Complete!")

  def revert_deployment(self): #pragma: no cover
    ''' Will revert back to original instances in autoscale group '''
    logging.error("REVERTING: Removing new instances from autoscale group")
    group_name = self.get_autoscale_group_name()
    new_instance_ids = self.gather_instance_info(group_name)
    for instance_id in new_instance_ids:
      try:
        self.conn_auto.terminate_instance(instance_id, decrement_capacity=True)
        logging.info("Removed {0} from autoscale group".format(instance_id))
      except:
        logging.warning('Failed to remove instance: {0}.'.format(instance_id))
    logging.error("REVERT COMPLETE!")
    exit(self.exit_error_code)

def get_args(): # pragma: no cover
  parser = argparse.ArgumentParser()
  parser.add_argument('-e', '--environment', action='store', dest='env', help='Environment e.g. qa, stg, prd', type=str, required=True)
  parser.add_argument('-p', '--project', action='store', dest='project', help='Project name', type=str, required=True)
  parser.add_argument('-b', '--build', action='store', dest='build_number', help='Build Number', type=str, required=True)
  parser.add_argument('-a', '--ami', action='store', dest='ami_id', help='AMI ID to be deployed', type=str, required=True)
  parser.add_argument('-P', '--profile', default='default', action='store', dest='profile', help='Profile name as designated in aws credentials/config files', type=str)
  parser.add_argument('-c', '--config', default='/opt/License2Deploy/regions.yml', action='store', dest='config', help='Config file Location, eg. /opt/License2Deploy/regions.yml', type=str)
  parser.add_argument('-s', '--stack', action='store', dest='stack_name', help='Stack name if AutoScaling Group created via CloudFormation', type=str)
  return parser.parse_args()

def main(): # pragma: no cover
  args = get_args()
  SetLogging.setup_logging()
  deployObj = RollingDeploy(args.env, args.project, args.build_number, args.ami_id, args.profile, args.config, args.stack_name)
  deployObj.deploy()
  
if __name__ == "__main__": # pragma: no cover
    main()
