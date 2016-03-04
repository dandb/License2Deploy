aws cloudformation update-stack --stack-name 'PtTestStack' --template-body '{
   "AWSTemplateFormatVersion":"2010-09-09",
   "Description":"Ec2",
   "Resources":{
      "PTLaunchConfigqa":{
         "Type":"AWS::AutoScaling::LaunchConfiguration",
         "Properties":{
            "ImageId":"ami-7b0aea3f",
            "InstanceType":"m1.medium"
         }
      },
      "PTELBConfigqa":{
         "Type":"AWS::ElasticLoadBalancing::LoadBalancer",
         "Properties":{
            "LoadBalancerName":"PTELBConfigqa",
            "HealthCheck": {
                    "HealthyThreshold": 3,
                    "Interval": 10,
                    "Target": "HTTP:80/ping",
                    "Timeout": 2,
                    "UnhealthyThreshold": 10
                },
            "Listeners":[
               {
                  "InstancePort":80,
                  "InstanceProtocol":"http",
                  "LoadBalancerPort":80,
                  "Protocol":"http"
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
                               "Value": "2",
                               "PropagateAtLaunch" : "true" }
                    ]
         }
      },
      "PTSNSTopicqa":{
         "Type":"AWS::SNS::Topic",
         "Properties":{
            "Subscription":[
               {
                  "Endpoint":"thatchinamoorthyp@dnb.com",
                  "Protocol":"email"
               }
            ]
         }
      },
      "PTScaleUpPolicyqa":{
         "Type":"AWS::AutoScaling::ScalingPolicy",
         "Properties":{
            "AdjustmentType":"PercentChangeInCapacity",
            "AutoScalingGroupName":{
               "Ref":"PTAutoScalingGroupqa"
            },
            "Cooldown":"300",
            "ScalingAdjustment":"20"
         }
      },
      "PTCloudWatchForCPUUtilizationqa":{
         "Type":"AWS::CloudWatch::Alarm",
         "Properties":{
            "AlarmDescription":"CPU Alarm for PT instance",
            "Namespace":"AWS/EC2",
            "MetricName":"CPUUtilization",
            "Statistic":"Average",
            "Period":"60",
            "EvaluationPeriods":"1",
            "Threshold":"6",
            "ComparisonOperator":"GreaterThanThreshold",
            "AlarmActions":[
               {
                  "Ref":"PTScaleUpPolicyqa"
               },
               {
                  "Ref":"PTSNSTopicqa"
               }
            ],
            "Dimensions":[
               {
                  "Name":"AutoScalingGroupName",
                  "Value":{
                     "Ref":"PTAutoScalingGroupqa"
                  }
               }
            ]
         }
      }
   }
}'