# Spot Price Fetcher
An script to fetch AWS spot instance pricing based on operating system and EC2 instance type.
Search can be filtered to specific availability-zones and/or date offset (up to the AWS API
maximum of 90 days).

The script is capable to be run as a stand-alone script or AWS lambda function (with or without
integration with AWS API Gateway).

## Standalone Execution
```
usage: spot-price-fetcher.py [-h] [-D DAYS] [-H HOURS] [-M MINUTES]
                             [-S SECONDS] [-o {linux,windows}] [-a AZ] [-m]
                             [-l {DEBUG,INFO,WARNING,ERROR,CRITICAL}] [-A]
                             type

Find AWS spot pricing for a given instance type

positional arguments:
  type                  Instance type to retrieve pricing for

optional arguments:
  -h, --help            show this help message and exit
  -D DAYS, --days DAYS  Number of days history to fetch
  -H HOURS, --hours HOURS
                        Number of hours history to fetch
  -M MINUTES, --minutes MINUTES
                        Number of minutes history to fetch
  -S SECONDS, --seconds SECONDS
                        Number of seconds history to fetch
  -o {linux,windows}, --os {linux,windows}
                        OS type to get pricing for
  -a AZ, --az AZ        Availability zones to filter pricing data (comma-
                        seperated)
  -m, --minimum         Also retrieve minimum price
  -l {DEBUG,INFO,WARNING,ERROR,CRITICAL}, --loglevel {DEBUG,INFO,WARNING,ERROR,CRITICAL}
                        Log level
  -A, --api             Simulate AWS API Gateway response
```

## AWS Lambda Setup
  * Runtime: Python 3.6
  * Memory (suggested): 384MB
  * Timeout (suggested): 10sec
  * IAM Permissions: Lambda Basic Execution service role (for Cloudwatch Logs) and at the very least
ec2:DescribeSpotPriceHistory (although it may be easier to use the AWS-managed `AmazonEC2ReadOnlyAccess` policy)

## AWS API Gateway Setup
  * Integration Type: Lambda Function (using Lambda Proxy Integration)

Setup method request as you see fit.  One example to sort of approximate how standalone execution works would be
to setup a GET Method Request using the instance type as a path parameter and the script command-line options as
URL Query String Parameters for the request.

EXAMPLE:
```
https://api-endpoint/{type}?os=windows&az=us-west-2a,us-west-2b&hours=96
```
where {type} is a valid instance type like `m4.large`
