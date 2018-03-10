#!/usr/bin/env python3

import boto3, json
import os, logging, datetime, time
from argparse import ArgumentParser

logging.basicConfig(level=logging.DEBUG)
logging.getLogger('botocore').setLevel(logging.WARNING)
logger = logging.getLogger('spot-price-fetcher')

def time_offset(e):
  offset = datetime.timedelta(
    days=int(e.get('days', 0)),
    hours=int(e.get('hours', 0)),
    minutes=int(e.get('minutes', 0)),
    seconds=int(e.get('seconds', 0))
  )

  # AWS API max
  if offset.days >= 90:
    offset = datetime.timedelta(days=90)

  return offset

def request_args(e):
  args = {
    'StartTime': datetime.datetime.utcnow() - time_offset(e),
    'EndTime': datetime.datetime.utcnow(),
    'InstanceTypes': [ e['type'] ],
    'ProductDescriptions': [ e['os'] ]
  }

  if e.get('az', False):
    args['Filters'] = [
      {
        'Name': 'availability-zone',
        'Values': e['az']
      }
    ]

  return args

def aws_client(az):
  svc = 'ec2'
  region = None
  boto3.setup_default_session()

  if az:
    for r in boto3.DEFAULT_SESSION.get_available_regions(svc):
      if az[0].startswith(r):
        region = r
        break

  logger.debug("REGION: %s", region)
  return boto3.client(svc, region_name=region)

def normalize_event(e):
  sys = 'Linux/UNIX (Amazon VPC)'
  evt = e.get('pathParameters', {})

  if evt.get('os', '').strip().casefold() == 'windows':
    sys = 'Windows (Amazon VPC)'

  evt['os'] = sys

  if 'queryStringParameters' in e:
    evt.update(e['queryStringParameters'])

    if evt.get('az', False):
      evt['az'] = evt['az'].split(',')

    if evt.get('minimum', False):
      evt['minimum'] = int(evt['minimum'])

  return evt

# AWS lambda compatible handler func
def handler(event, context):
  evt = normalize_event(event)

  if 'loglevel' in evt and evt['loglevel']:
    logger.setLevel(evt['loglevel'])
  else:
    logger.setLevel(os.environ.get('LOG_LEVEL', 'INFO'))

  logger.debug(evt)

  c = aws_client(evt.get('az'))
  args  = request_args(evt)
  vals  = []
  done  = False
  token = None

  # multiprocessing.Pool() is not available on AWS lambda, but the filtered dataset
  # is small enough that there's no substantial exec time difference with this method
  t0 = time.monotonic()
  while not done:
    if token:
      args['NextToken'] = token

    r = c.describe_spot_price_history(**args)
    s = sorted(map(lambda x: float(x['SpotPrice']), r['SpotPriceHistory']))
    vals.extend([min(s), max(s)])

    if r.get('NextToken', False) and len(r['NextToken']) > 0:
      token = r['NextToken']
    else:
      done = True

    logger.debug("FETCH TIME: %.03f sec", time.monotonic() - t0)

  body = max(vals)
  if evt.get('minimum', False):
    body = { 'min': min(vals), 'max': max(vals) }

  if 'httpMethod' in event:
    # Looks like a lambda/API gateway request
    res = {'statusCode': 200, 'headers': {'Content-Type': 'application/json'}, 'body': json.dumps(body)}
    return json.dumps(res)
  else:
    return json.dumps(body)

if __name__ == '__main__':
  p = ArgumentParser(description='Find AWS spot pricing for a given instance type')
  p.add_argument('-D', '--days',  type=int, default=0, help='Number of days history to fetch')
  p.add_argument('-H', '--hours', type=int, default=0, help='Number of hours history to fetch')
  p.add_argument('-M', '--minutes', type=int, default=0, help='Number of minutes history to fetch')
  p.add_argument('-S', '--seconds', type=int, default=0, help='Number of seconds history to fetch')
  p.add_argument('-o', '--os', choices=['linux', 'windows'], default='linux', help='OS type to get pricing for')
  p.add_argument('-a', '--az', help='Availability zones to filter pricing data (comma-seperated)')
  p.add_argument('-m', '--minimum', action='store_true', help='Also retrieve minimum price')
  p.add_argument('-l', '--loglevel', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'], help='Log level')
  p.add_argument('-A', '--api', action='store_true', help='Simulate AWS API Gateway response')
  p.add_argument('type', help='Instance type to retrieve pricing for')

  args = p.parse_args()
  e = {
    "pathParameters": {"os": args.os, "type": args.type},
    "queryStringParameters": {
      "days":  args.days,
      "hours": args.hours,
      "minutes": args.minutes,
      "seconds": args.seconds,
      "az": args.az,
      "minimum": args.minimum,
      "loglevel": args.loglevel
    }
  }

  if args.api:
    e['httpMethod'] = 'GET'

  print(handler(e, None))

# Sample event sent via API gateway to AWS lambda
# (note: need to pass 'az' query param as a single comma-seperated value)
# {
#   "pathParameters": {"os":"linux","type":"t2.medium"},
#   "queryStringParameters":{"days":"90","az":"us-east-2a,us-east-2b","minimum":"1"}
# }
