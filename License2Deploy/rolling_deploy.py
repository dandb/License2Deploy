'''
Created on Sep 2, 2015

@author: thatchinamoorthyp
'''

def return_autoscalinggroup_desired_size():
    """ AWS Call: return the  minsize of the AutoScaling Group of the Microservice"""
    return 5

def calculate_new_desired_ec2_count(current_desired_ec2_count):
    """ By default, we double the instance Count """
    return 2 * current_desired_ec2_count

def update_desired_ec2_count_in_autoscalinggroup(desired_ec2_count):
    """ AWS Call: update the desired_size of the AutoScaling Group of the Microserice"""
    pass

def healthcheck_new_instances():
    """ AWS Call: Check whether the new instances are working good """
    return True


def update_ami_id_with_last_successfull():
    """ AWS Call: As health check failed, update the ami_id with the last successfull one """
    pass


def rolling_deploy():
    current_desired_ec2_count = return_autoscalinggroup_desired_size()
    new_desired_ec2_count = calculate_new_desired_ec2_count(current_desired_ec2_count)
    update_desired_ec2_count_in_autoscalinggroup(new_desired_ec2_count)
    if (healthcheck_new_instances()):
        print "Health Check Passed"
        update_desired_ec2_count_in_autoscalinggroup(current_desired_ec2_count)
    else:    
        print "Health Check Failed"
        update_ami_id_with_last_successfull()        
        update_desired_ec2_count_in_autoscalinggroup(current_desired_ec2_count)
        
if __name__ == '__main__':
    rolling_deploy()  
    
   