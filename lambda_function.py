"""
This sample demonstrates an implementation of the Lex Code Hook Interface
in order to serve a sample bot which manages reservations for hotel rooms and car rentals.
Bot, Intent, and Slot models which are compatible with this sample can be found in the Lex Console
as part of the 'BookTrip' template.

For instructions on how to set up and test this bot, as well as additional samples,
visit the Lex Getting Started documentation http://docs.aws.amazon.com/lex/latest/dg/getting-started.html.
"""

import json
import datetime
import time
import os
import dateutil.parser
import logging

import boto3

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
logging.getLogger('botocore').setLevel(logging.CRITICAL)
logging.getLogger('boto3').setLevel(logging.CRITICAL)

# tuple vCPU, Memory (in GB)
INSTANCE_TYPES = {'t2.nano': (1,0.5),
                  't2.micro': (1,1), 
                  't2.small': (1,2), 
                  't2.medium': (2,4), 
                  't2.large': (2,8), 
                  't2.xlarge': (4,16), 
                  't2.2xlarge': (8,32), 
                  'm4.large': (2,8), 
                  'm4.xlarge': (4,16), 
                  'm4.2xlarge': (8,32), 
                  'm4.4xlarge': (16,64), 
                  'm4.10xlarge': (40,160), 
                  'm4.16xlarge': (64,256), 
                  'm3.medium': (1,3.75), 
                  'm3.large': (2,7.5), 
                  'm3.xlarge': (4,15), 
                  'm3.2xlarge': (8,30), 
                  'c4.large': (2,3.75), 
                  'c4.xlarge': (4,7.5), 
                  'c4.2xlarge': (8,15), 
                  'c4.4xlarge': (16,30), 
                  'c4.8xlarge': (36,60), 
                  'c3.large': (2,3.75), 
                  'c3.xlarge': (4,7.5), 
                  'c3.2xlarge': (8,15), 
                  'c3.4xlarge': (16,30), 
                  'c3.8xlarge': (32,60), 
                  'r3.large': (2,15.25), 
                  'r3.xlarge': (4,30.5), 
                  'r3.2xlarge': (8,61), 
                  'r3.4xlarge': (16,122), 
                  'r3.8xlarge': (32,244), 
                  'r4.large': (2,15.25), 
                  'r4.xlarge': (4,30.5), 
                  'r4.2xlarge': (8,61), 
                  'r4.4xlarge': (16,122), 
                  'r4.8xlarge': (32,244), 
                  'r4.16xlarge': (64,488), 
                  'x1.16xlarge': (64,976), 
                  'x1.32xlarge': (128,1952), 
                  'd2.xlarge': (4,30.5), 
                  'd2.2xlarge': (8,61), 
                  'd2.4xlarge': (16,122), 
                  'd2.8xlarge': (36,244), 
                  'i2.xlarge': (4,30.5), 
                  'i2.2xlarge': (8,61), 
                  'i2.4xlarge': (16,122), 
                  'i2.8xlarge': (32,244), 
                  'i3.large': (2,15.25), 
                  'i3.xlarge': (4,30.5), 
                  'i3.2xlarge': (8,61), 
                  'i3.4xlarge': (16,122), 
                  'i3.8xlarge': (32,244), 
                  'i3.16xlarge': (64,488), 
                  'f1.2xlarge': (8,122), 
                  'f1.16xlarge': (64,976), 
                  'p2.xlarge': (4,61), 
                  'p2.8xlarge': (32,488), 
                  'p2.16xlarge': (64,732), 
                  'g2.2xlarge': (8,15), 
                  'g2.8xlarge': (32,60), 
                  'm1.small': (1,1.7), 
                  'm1.medium': (1,3.75), 
                  'm1.large': (2,7.5), 
                  'm1.xlarge': (4,15), 
                  'c1.medium': (2,1.7), 
                  'c1.xlarge': (8,7), 
                  'cc2.8xlarge': (32,60.5), 
                  'm2.xlarge': (2,17.1), 
                  'm2.2xlarge': (4,34.2), 
                  'm2.4xlarge': (8,68.4), 
                  'cr1.8xlarge': (32,244), 
                  'hi1.4xlarge': (16,60.5), 
                  'hs1.8xlarge': (16,117), 
                  'cg1.4xlarge': (16,22.5), 
                  't1.micro': (1,0.6)
                }

# --- Helpers that build all of the responses ---


def elicit_slot(session_attributes, intent_name, slots, slot_to_elicit, message):
    return {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'ElicitSlot',
            'intentName': intent_name,
            'slots': slots,
            'slotToElicit': slot_to_elicit,
            'message': message
        }
    }


def close(session_attributes, fulfillment_state, message):
    response = {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'Close',
            'fulfillmentState': fulfillment_state,
            'message': message
        }
    }

    return response


def delegate(session_attributes, slots):
    return {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'Delegate',
            'slots': slots
        }
    }


# --- Helper Functions ---

def isvalid_instance_type(instance_type):
    # TODO: use regex instead of fixed list
    instance_types = INSTANCE_TYPES.keys()
    return instance_type.lower() in instance_types

def isvalid_amazon_region(amazon_region):
    amazon_regions = ['us-east-2', 'us-east-1', 'us-west-1', 'us-west-2','ca-central-1', 'ap-south-1', 'ap-northeast-2', 
                      'ap-southeast-1', 'ap-southeast-2', 'ap-northeast-1', 'eu-central-1', 'eu-west-1', 'eu-west-2', 
                      'sa-east-1']
    return amazon_region.lower() in amazon_regions

def isvalid_memory(memory):
    """
    It's not valid if the memory is expressed in something else than GB
    """
    invalid_units = ['kb', 'mb', 'tb', 'pt']
    for unit in invalid_units:
        if unit in memory.lower():
            return False
    else:
        return True


def get_instances(cpu,memory):
    """
    Return a list of instances that fulfill the requirements
    """
    cpu = int(cpu)
    memory = int(memory)
    instances = []

    for instance, resource in INSTANCE_TYPES.iteritems():
        if resource[0] >= cpu and resource[1] >= memory:
            instances.append(instance)

    return instances


def build_validation_result(isvalid, violated_slot, message_content):
    return {
        'isValid': isvalid,
        'violatedSlot': violated_slot,
        'message': {'contentType': 'PlainText', 'content': message_content}
    }

def validate_get_current_spot_price(slots):
    instance_type = slots.get('InstanceType') if slots else None
    amazon_region = slots.get('AmazonRegion') if slots else None

    if instance_type and not isvalid_instance_type(instance_type):
        return build_validation_result(
            False,
            'InstanceType',
            'We currently do not support {} as a valid instance type.  Can you try a different instance type?'.format(instance_type)
        )

    if amazon_region and not isvalid_amazon_region(amazon_region):
        # specific message in case the person tried to get his own region information
        if amazon_region == 'my region':
            message = 'Sorry, I\'m not that smart! What is your region?'
        else:
            message = 'We currently do not support {} as a valid Amazon region.  Can you try a different Amazon region?'.format(amazon_region)
        return build_validation_result(
            False,
            'AmazonRegion',
            message
        )

    if instance_type and amazon_region and not get_price_history([instance_type], amazon_region):
        return build_validation_result(
            False,
            'InstanceType',
            ('I am afraid I cannot get this information. {} might not be available as a spot instance in {}. '
             'Please enter another instance type').format(instance_type, amazon_region)
        )

    return {'isValid': True}

def validate_get_cheapest_spot_price(slots):
    amazon_region = slots.get('AmazonRegion') if slots else None
    memory = slots.get('Memory') if slots else None
    cpu = slots.get('CPUs') if slots else None

    if amazon_region and not isvalid_amazon_region(amazon_region):
        # specific message in case the person tried to get his own region information
        if amazon_region == 'my region':
            message = 'Sorry, I\'m not that smart! What is your region?'
        else:
            message = 'We currently do not support {} as a valid Amazon region.  Can you try a different Amazon region?'.format(amazon_region)
        return build_validation_result(
            False,
            'AmazonRegion',
            message
        )

    if memory and not isvalid_memory(memory):
        return build_validation_result(
            False,
            'Memory',
            'We currently only support GB as a memory unit. How much memory do you require in GB?'
        )


    # if instance_type and amazon_region and not get_price_history([instance_type], amazon_region):
    #     return build_validation_result(
    #         False,
    #         'InstanceType',
    #         ('I am afraid I cannot get this information. {} might not be available as a spot instance in {}. '
    #          'Please enter another instance type').format(instance_type, amazon_region)
    #     )

    return {'isValid': True}


""" --- Backend function getting the requested information --- """


def call_spot_price_api(instance_types, amazon_region):
    client = boto3.client('ec2', region_name=amazon_region)

    try:
        response = client.describe_spot_price_history(
            StartTime=datetime.datetime.utcnow(),
            InstanceTypes=instance_types,
            ProductDescriptions=['Linux/UNIX (Amazon VPC)']
        )
    except Exception as e:
        logger.exception(e)
        return []

    return response


def get_price_history(instance_type, amazon_region):

    response = call_spot_price_api(instance_type, amazon_region)

    prices = []
    # return a list of tuples [(price, availability-zone)]
    for price in response['SpotPriceHistory']:
        prices.append((float(price['SpotPrice']), price['AvailabilityZone']))

    return prices


def get_cheapest_instance(instances, amazon_region):

    if instances:
        response = call_spot_price_api(instances, amazon_region)

        # we first find the cheapest instance type
        minimum_price = float('inf')
        instance_type = ''
        availability_zone = ''
        for instance in response['SpotPriceHistory']:
            price = float(instance['SpotPrice'])
            if price < minimum_price:
                minimum_price = price
                instance_type = instance['InstanceType']
                availability_zone = instance['AvailabilityZone']

        prices = []
        # if we found something, we get the other instance types with the same price
        if instance_type:
            for instance in response['SpotPriceHistory']:
                price = float(instance['SpotPrice'])
                if price == minimum_price:
                    prices.append((instance['InstanceType'], price, instance['AvailabilityZone']))

        return prices
    else:
        return []


def format_price_answer(spot_prices):
    """
    Receive a list of tuples [(price, availability-zone)]
    Return a string
    """
    return "\n".join("*{}$* per hour in {}".format(*price) for price in spot_prices)


def format_cheapest_answer(spot_prices_result, amazon_region, memory, cpu):
    """
    spot_prices_result is a list of tuples [(instance_type, price, availability-zone)]
    Return a string
    """
    message = 'The cheapest instances in {} with at least {} GB of memory and {} CPUs '.format(amazon_region, memory, cpu) + \
        'are currently at *{}$* per hour. The instance types are: \n'.format(spot_prices_result[0][1])
    instances = ""
    for instance in spot_prices_result:
        instances += '{} ({} vCPUs, {} GB in {})\n'.format(instance[0], INSTANCE_TYPES.get(instance[0])[0], INSTANCE_TYPES.get(instance[0])[1], instance[2])
    message += instances
    return message

""" --- Functions that control the bot's behavior --- """

def get_current_spot_price(intent_request):
    """
    Performs dialog management and fulfillment for booking a car.

    Beyond fulfillment, the implementation for this intent demonstrates the following:
    1) Use of elicitSlot in slot validation and re-prompting
    2) Use of sessionAttributes to pass information that can be used to guide conversation
    """
    logger.debug('Current Intent: {}'.format(intent_request['currentIntent']))
    current = intent_request.get('currentIntent')
    slots = current.get('slots') if current else None
    instance_type = slots.get('InstanceType') if slots else None
    amazon_region = slots.get('AmazonRegion') if slots else None
    # confirmation_status = current['confirmationStatus']
    session_attributes = intent_request['sessionAttributes'] if intent_request.get('sessionAttributes') is not None else {}

    if intent_request['invocationSource'] == 'DialogCodeHook':
        # Validate any slots which have been specified.  If any are invalid, re-elicit for their value
        validation_result = validate_get_current_spot_price(intent_request['currentIntent']['slots'])
        if not validation_result['isValid']:
            slots[validation_result['violatedSlot']] = None
            return elicit_slot(
                session_attributes,
                intent_request['currentIntent']['name'],
                slots,
                validation_result['violatedSlot'],
                validation_result['message']
            )

        # Otherwise, let native DM rules determine how to elicit for slots and/or drive confirmation.
        return delegate(session_attributes, intent_request['currentIntent']['slots'])


    # Display value. Call backend
    # We get the info and we format the answer
    spot_prices_result = get_price_history([instance_type], amazon_region)
    spot_prices_message = format_price_answer(spot_prices_result)

    logger.debug('Current price  for {} instance type in {} is {}'.format(instance_type, amazon_region, spot_prices_message))
    return close(
        session_attributes,
        'Fulfilled',
        {
            'contentType': 'PlainText',
            'content': 'The current spot price for a {} instance in {} is \n{}.'.format(instance_type, amazon_region, spot_prices_message)
        }
    )

def get_cheapest_spot_price(intent_request):
    logger.debug('Current Intent: {}'.format(intent_request['currentIntent']))
    current = intent_request.get('currentIntent')
    slots = current.get('slots') if current else None
    amazon_region = slots.get('AmazonRegion') if slots else None
    confirmation_status = current.get('confirmationStatus') if current else None
    session_attributes = intent_request['sessionAttributes'] if intent_request.get('sessionAttributes') is not None else {}

    if intent_request['invocationSource'] == 'DialogCodeHook':
        # Validate any slots which have been specified.  If any are invalid, re-elicit for their value
        validation_result = validate_get_cheapest_spot_price(intent_request['currentIntent']['slots'])
        if not validation_result['isValid']:
            slots[validation_result['violatedSlot']] = None
            return elicit_slot(
                session_attributes,
                intent_request['currentIntent']['name'],
                slots,
                validation_result['violatedSlot'],
                validation_result['message']
            )

        # Otherwise, let native DM rules determine how to elicit for slots and/or drive confirmation.
        return delegate(session_attributes, slots)


    # # Display value. Call backend
    # We get the info and we format the answer

    # first we format the inputs
    cpu = slots.get('CPUs') if slots.get('CPUs') else '1'

    if not slots.get('Memory') or not slots.get('Memory')[0].isdigit():
        memory = '1'
    else:
        # we transform the memory into digits only
        if slots.get('Memory').isdigit():
            memory = slots.get('Memory')
        else:
            memory = ''
            for c in slots.get('Memory'):
                if c.isdigit():
                    memory += str(c)
                else:
                    break

    instances = get_instances(cpu,memory)
    spot_prices_result = get_cheapest_instance(instances, amazon_region)

    if not spot_prices_result:
        message = "Sorry, we couldn't find instances available in {} with at least {} GB of memory and {} CPUs.".format(amazon_region, memory, cpu)
    else:
        message = format_cheapest_answer(spot_prices_result, amazon_region, memory, cpu)

    logger.debug(message)
    return close(
        session_attributes,
        'Fulfilled',
        {
            'contentType': 'PlainText',
            'content': message
        }
    )

# --- Intents ---


def dispatch(intent_request):
    """
    Called when the user specifies an intent for this bot.
    """

    logger.debug('dispatch userId={}, intentName={}'.format(intent_request['userId'], intent_request['currentIntent']['name']))

    intent_name = intent_request['currentIntent']['name']

    # Dispatch to your bot's intent handlers
    if intent_name == 'GetCurrentSpotInstancePrice':
        return get_current_spot_price(intent_request)
    elif intent_name == 'GetCheapestSpotInstancesWithAtLeast':
        return get_cheapest_spot_price(intent_request)

    raise Exception('Intent with name ' + intent_name + ' not supported')


# --- Main handler ---


def lambda_handler(event, context):
    """
    Route the incoming request based on intent.
    The JSON body of the request is provided in the event slot.
    """
    logger.debug('event.bot.name={}'.format(event['bot']['name']))

    return dispatch(event)
