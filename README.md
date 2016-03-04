[![Build Status](https://travis-ci.org/dandb/License2Deploy.svg)](https://travis-ci.org/dandb/License2Deploy)
[![Coverage Status](https://coveralls.io/repos/dandb/License2Deploy/badge.svg?branch=master&service=github)](https://coveralls.io/github/dandb/License2Deploy?branch=master)
# License2Deploy

Rolling deploys for AWS AutoScale Groups

==================
What is License2Deploy?
==================

License2Deploy is an automated solution for rolling deployments in AWS written in python. 

The rolling deployment will:
 - Double your instances in your autoscale group
 - Confirm that the instances are healthy
 - Confirm that the new instances are InService in the Elastic Load Balanacer
 - Drop your autoscale group instance count back to what it was at prior to deployment
 - Ensure that the old instances are out of the load balancer

Usage
==================
```
usage: rolling_deploy.py [-h] -e ENV -p PROJECT -b BUILDNUM -a AMIID
                         [-P PROFILE] [-c CONFIG]

optional arguments:
  -h, --help            show this help message and exit
  -e ENV, --environment ENV
                        Environment
  -p PROJECT, --project PROJECT
                        Project name
  -b BUILDNUM, --build BUILDNUM
                        Build Number
  -a AMIID, --ami AMIID
                        AMI ID
  -P PROFILE, --profile PROFILE
                        Profile name as designated in aws credentials/config
                        files
  -c CONFIG, --config CONFIG
                        Config file Location, eg.
                        /opt/License2Deploy/config.yml
```
Requirements
==================

There are a few requirements in order for the automated rolling deployments to work:

1. As stated above, this has to be done in AWS (Amazon Web Services)
2. You need an autoscale group
3. Instances in the autoscale group need to be behind an Elastic Load Balancer (ELB)
4. All instances in the autoscale group need to be tagged with a build number
  * This is an important step as when the script runs, it will differentiate the old builds
    from the new builds based off of the build number that is passed in as a command line parameter
5. The credentials for the user need to be in the ~/.aws/credentials file and if not passed in as a 
   command line argument, the script will look at the 'default' profile.
6. The script needs the AMI ID of the instances that will be built.
  * The reason for the AMI ID is to ensure that if it was just created, it is not in a pending state
    and it is ready to be used to build an instance.
7. Lastly, you should modify the regions.yml file to fit your environment as the environment is what is
   passed to the script, and the script will work the logic out based on what is in the yaml config.
  * Example of environments: qa, stg, prd, dev, test, etc.

Development
============

python setup.py install

python setup.py test

python License2Deploy/rolling_deploy.py


Sample Testing
===============
Use Case: `ami-37285b57 with BUILD=1 Tag` should be replaced / (rolling deploy) with `ami-78245718 with BUILD=2 Tag`. 
    - Both these AMIs is a linux ami with apache running that woulk respond for "index.html".

Step 1: Create AMIs. For testing, lets reuse public amis - "ami-37285b57" and "ami-78245718". If you have properly built app AMIs, please use that.

Step 2: Create a Tag "BUILD" which denotes the CI build number
  - Command: 
      - aws ec2 create-tags --tags --resources ami-37285b57 --tags Key=BUILD,Value=1
      - aws ec2 create-tags --tags --resources ami-78245718 --tags Key=BUILD,Value=2
      
Step 3: Create a Stack with AMI as ami-37285b57, and the ASG will create 2 EC2 instances with the tag BUILD:1.
  - Command:
      - ./CreateTestStack.sh
  - Note:
      - Update your  public key name on "KeyName" at line no 10

Step 4: Update the Stack with AMI as ami-78245718, whose tag is  BUILD:2
  - Command:
      - ./UpdateTestStack.sh
  - Note:
      - Update your  public key name on "KeyName" at line no 10

Step 5: Run the Rolling deploy to kill the old EC2 instance with tag BUILD:1 (ami-37285b57) , and spun of 2 new EC2 instances with tag BUILD:2 (ami-78245718)
  - Command:
      - sudo python License2Deploy/rolling_deploy.py -e qa -p PT -b 2 -a ami-78245718
  - Note:
      - where, -e is environment, -p is applicaiton project, -b is BUILD Tag value, -a is AMI ID
      - your name of the ASG, LB, LC should have the string - project name and environment name, so that the rolling-deploy script can pick the right one.
      - Place your regions.yml at /opt/License2Deploy/regions.yml
      - If you are using multiple profile for aws-credentials, mention your aws profile by adding another param -P xyz
      
      
Step 6: To Delete the Stack
  - Command:
      - aws cloudformation delete-stack --stack-name 'PtTestStack'