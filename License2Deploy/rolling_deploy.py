import boto.ec2.autoscale as asg

class RollingDeploy:

    def init(self):
        self.aws_connection = asg.connect_to_region('us-east-1')
    
    def return_autoscalinggroup_desired_size(self, auto_scaling_group):
        """ AWS Call: return the  minsize of the AutoScaling Group of the Microservice"""
        return auto_scaling_group.min_size
    
    def calculate_new_desired_ec2_count(self, current_desired_ec2_count):
        """ By default, we double the instance Count """
        return 2 * current_desired_ec2_count
    
    def update_desired_ec2_count_in_autoscalinggroup(self, auto_scaling_group, ec2_count):
        auto_scaling_group.set_capacity(ec2_count)
        """ AWS Call: update the desired_size of the AutoScaling Group of the Microserice"""
        pass
    
    def healthcheck_new_instances(self):
        """ AWS Call: Check whether the new instances are working good """
        return True
    
    def retrieve_auto_scaling_group(self, app_name, project_name, environment):
        """ AWS Call: retrieve the Auto Scaling Group by Tag """
        auto_scaling_groups = self.aws_connection.get_all_groups();
        return self.filter_auto_scaling_group(auto_scaling_groups, app_name, project_name, environment)
    
    def filter_auto_scaling_group(self, auto_scaling_groups, app_name, project_name, environment):
        """ Filter out the correct auto scaling group """
        pattern = app_name + "-backend-" + environment+ "-" + app_name + project_name
        for auto_scaling_group in auto_scaling_groups:
            if (auto_scaling_group.name.find(pattern) > -1):
                return auto_scaling_group
            
    def wait_for_new_instances_to_spun_up(self):
        """  check the status of the instance and wait for it to startup and become available for testing. """
        pass
    
    def rolling_deploy(self):
        auto_scaling_group = self.retrieve_auto_scaling_group()
        current_desired_ec2_count = self.return_autoscalinggroup_desired_size(auto_scaling_group)
        new_desired_ec2_count = self.calculate_new_desired_ec2_count(current_desired_ec2_count)
        self.update_desired_ec2_count_in_autoscalinggroup(auto_scaling_group, new_desired_ec2_count)
        self.wait_for_new_instances_to_spun_up()
        if (self.healthcheck_new_instances()):
            print "Health Check Passed"
            self.update_desired_ec2_count_in_autoscalinggroup(auto_scaling_group, current_desired_ec2_count)
        else:
            print "Health Check Failed"
            return "Error"