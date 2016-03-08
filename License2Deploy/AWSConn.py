#!/usr/bin/python

import boto.ec2 as ec2
import boto.ec2.autoscale as a
import boto.ec2.elb as elb
import boto.ec2.cloudwatch as cloudwatch
import logging
import yaml

class AWSConn(object):

  @staticmethod
  def aws_conn_auto(region, profile='default'):
    try:
      conn = a.connect_to_region(region, profile_name=profile)
      return conn
    except Exception as e:
      logging.error("Unable to connect to region, please investigate: {0}".format(e))

  @staticmethod
  def aws_conn_ec2(region, profile='default'):
    try: 
      conn = ec2.connect_to_region(region, profile_name=profile)
      return conn
    except Exception as e:
      logging.error("Unable to connect to region, please investigate: {0}".format(e))

  @staticmethod
  def aws_conn_elb(region, profile='default'):
    try:
      conn = elb.connect_to_region(region, profile_name=profile)
      return conn
    except Exception as e:
      logging.error("Unable to connect to region, please investigate: {0}".format(e))

  @staticmethod
  def aws_conn_cloudwatch(region, profile='default'):
    try: 
      conn = cloudwatch.connect_to_region(region, profile_name=profile)
      return conn
    except Exception as e:
      logging.error("Unable to connect to region, please investigate: {0}".format(e))

  @staticmethod
  def load_config(config):
    with open(config, 'r') as stream:
      return yaml.load(stream)

  @staticmethod
  def determine_region(reg):
    reg_list = [region.name for region in ec2.regions()]
    if reg in reg_list:
      return reg
    else:
      logging.warning("Unable to get region info. Environment requested: {0}. Regions available: {1}. Returning the default region of us-west-1".format(reg, reg_list))
      return 'us-west-1' #Returning us-west-1 as a default region
