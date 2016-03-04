aws cloudformation create-stack --stack-name 'PtTestStack' --template-body '{
   "AWSTemplateFormatVersion":"2010-09-09",
   "Description":"Ec2",
   "Resources":{
      "PTLaunchConfigqa":{
         "Type":"AWS::AutoScaling::LaunchConfiguration",
         "Properties":{
            "ImageId":"ami-37285b57",
            "InstanceType":"m1.medium",
            "KeyName":"DBCC_DEV_KeyPair"
         }
      },
      "PTELBConfigqa":{
         "Type":"AWS::ElasticLoadBalancing::LoadBalancer",
         "Properties":{
            "LoadBalancerName":"PTELBConfigqa",
            "HealthCheck": {
                    "HealthyThreshold": 3,
                    "Interval": 10,
                    "Target": "HTTP:80/index.html",
                    "Timeout": 2,
                    "UnhealthyThreshold": 10
                },
            "Listeners":[
               {
                  "InstancePort":80,
                  "InstanceProtocol":"http",
                  "LoadBalancerPort":80,
                  "Protocol":"http"
               },
                {
                    "InstancePort": 443,
                    "InstanceProtocol": "http",
                    "LoadBalancerPort": 443,
                    "Protocol": "http"
                }
            ],
            "AvailabilityZones":[
               "us-west-1a"
            ]
         }
      },
      "PTAutoScalingGroupqa":{
         "Type":"AWS::AutoScaling::AutoScalingGroup",
         "Properties":{
            "LaunchConfigurationName":{
               "Ref":"PTLaunchConfigqa"
            },
            "AvailabilityZones":[
               "us-west-1a"
            ],
            "LoadBalancerNames":[{
               "Ref":"PTELBConfigqa"
            }],
            "MinSize":"2",
            "MaxSize":"4",
            "Tags" : [
                             { "Key": "BUILD",
                               "Value": "1",
                               "PropagateAtLaunch" : "true" }
                    ]
         }
      }
    }
}'