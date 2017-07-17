# Created by Celine Aussourd
#
# Copyright (c) 2017 Sandtable Ltd. All rights reserved.

"""
Lex Code Hook Interface to serve sbot which provides information about
AWS Spot prices.

"""

import datetime
import logging

import boto3

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
logging.getLogger('botocore').setLevel(logging.CRITICAL)
logging.getLogger('boto3').setLevel(logging.CRITICAL)

# tuple vCPU, Memory (in GB)
INSTANCE_TYPES = {'t1.micro': (1, 0.6),
                  't2.nano': (1, 0.5),
                  't2.micro': (1, 1),
                  't2.small': (1, 2),
                  't2.medium': (2, 4),
                  't2.large': (2, 8),
                  't2.xlarge': (4, 16),
                  't2.2xlarge': (8, 32),
                  'm1.small': (1, 1.7),
                  'm1.medium': (1, 3.75),
                  'm1.large': (2, 7.5),
                  'm1.xlarge': (4, 15),
                  'm2.xlarge': (2, 17.1),
                  'm2.2xlarge': (4, 34.2),
                  'm2.4xlarge': (8, 68.4),
                  'm3.medium': (1, 3.75),
                  'm3.large': (2, 7.5),
                  'm3.xlarge': (4, 15),
                  'm3.2xlarge': (8, 30),
                  'm4.large': (2, 8),
                  'm4.xlarge': (4, 16),
                  'm4.2xlarge': (8, 32),
                  'm4.4xlarge': (16, 64),
                  'm4.10xlarge': (40, 160),
                  'm4.16xlarge': (64, 256),
                  'c1.medium': (2, 1.7),
                  'c1.xlarge': (8, 7),
                  'c3.large': (2, 3.75),
                  'c3.xlarge': (4, 7.5),
                  'c3.2xlarge': (8, 15),
                  'c3.4xlarge': (16, 30),
                  'c3.8xlarge': (32, 60),
                  'c4.large': (2, 3.75),
                  'c4.xlarge': (4, 7.5),
                  'c4.2xlarge': (8, 15),
                  'c4.4xlarge': (16, 30),
                  'c4.8xlarge': (36, 60),
                  'r3.large': (2, 15.25),
                  'r3.xlarge': (4, 30.5),
                  'r3.2xlarge': (8, 61),
                  'r3.4xlarge': (16, 122),
                  'r3.8xlarge': (32, 244),
                  'r4.large': (2, 15.25),
                  'r4.xlarge': (4, 30.5),
                  'r4.2xlarge': (8, 61),
                  'r4.4xlarge': (16, 122),
                  'r4.8xlarge': (32, 244),
                  'r4.16xlarge': (64, 488),
                  'x1.16xlarge': (64, 976),
                  'x1.32xlarge': (128, 1952),
                  'd2.xlarge': (4, 30.5),
                  'd2.2xlarge': (8, 61),
                  'd2.4xlarge': (16, 122),
                  'd2.8xlarge': (36, 244),
                  'i2.xlarge': (4, 30.5),
                  'i2.2xlarge': (8, 61),
                  'i2.4xlarge': (16, 122),
                  'i2.8xlarge': (32, 244),
                  'i3.large': (2, 15.25),
                  'i3.xlarge': (4, 30.5),
                  'i3.2xlarge': (8, 61),
                  'i3.4xlarge': (16, 122),
                  'i3.8xlarge': (32, 244),
                  'i3.16xlarge': (64, 488),
                  'f1.2xlarge': (8, 122),
                  'f1.16xlarge': (64, 976),
                  'p2.xlarge': (4, 61),
                  'p2.8xlarge': (32, 488),
                  'p2.16xlarge': (64, 732),
                  'g2.2xlarge': (8, 15),
                  'g2.8xlarge': (32, 60),
                  'cc2.8xlarge': (32, 60.5),
                  'cr1.8xlarge': (32, 244),
                  'hi1.4xlarge': (16, 60.5),
                  'hs1.8xlarge': (16, 117),
                  'cg1.4xlarge': (16, 22.5)
                  }

AMAZON_REGIONS = ['us-east-2', 'us-east-1', 'us-west-1', 'us-west-2',
                  'ca-central-1', 'ap-south-1', 'ap-northeast-2',
                  'ap-southeast-1', 'ap-southeast-2', 'ap-northeast-1',
                  'eu-central-1', 'eu-west-1', 'eu-west-2', 'sa-east-1']


# --- Helpers that build all of the responses ---


def elicit_slot(session_attributes, intent_name, slots, slot_to_elicit,
                message):
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
    instance_types = INSTANCE_TYPES.keys()
    return instance_type.lower() in instance_types


def isvalid_amazon_region(amazon_region):
    return amazon_region.lower() in AMAZON_REGIONS


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


def get_instances(cpu, memory):
    """
    Return a list of instances that fulfill the requirements (CPU and RAM)
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
        message = (
            'We currently do not support {} as a valid instance type. '
            'Can you try a different instance type?'.format(instance_type)
        )
        return build_validation_result(False, 'InstanceType', message)

    if amazon_region and not isvalid_amazon_region(amazon_region):
        message = (
            'We currently do not support {} as a valid Amazon region. '
            'Can you try a different Amazon region?'.format(amazon_region)
        )
        return build_validation_result(False, 'AmazonRegion', message)

    # check if that instance type is available as spot instance in that region
    if (instance_type and amazon_region and
            not get_price_history([instance_type], amazon_region)):
        message = (
            'I am afraid I cannot get this information. '
            '{} might not be available as a spot instance in {}. Please '
            'enter another instance type'.format(instance_type, amazon_region)
        )
        return build_validation_result(False, 'InstanceType', message)

    return {'isValid': True}


def validate_get_cheapest_spot_price(slots):
    amazon_region = slots.get('AmazonRegion') if slots else None
    memory = slots.get('Memory') if slots else None

    if amazon_region and not isvalid_amazon_region(amazon_region):
        message = (
            'We currently do not support {} as a valid Amazon region. '
            'Can you try a different Amazon region?'.format(amazon_region)
        )
        return build_validation_result(False, 'AmazonRegion', message)

    if memory and not isvalid_memory(memory):
        message = (
            'We currently only support GB as a memory unit. '
            'How much memory do you require in GB?'
        )
        return build_validation_result(False, 'Memory', message)

    return {'isValid': True}


def validate_get_instance_types(slots):
    memory = slots.get('Memory') if slots else None

    if memory and not isvalid_memory(memory):
        message = (
            'We currently only support GB as a memory unit. '
            'How much memory do you require in GB?'
        )
        return build_validation_result(False, 'Memory', message)

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
    """
    Return the prices ([isntance_type, price, availability_zone])
    of the cheapeast instances
    """
    if instances:
        # get the current spot prices
        response = call_spot_price_api(instances, amazon_region)

        # we first find the cheapest instance type
        minimum_price = float('inf')
        is_instance_type = False
        for instance in response['SpotPriceHistory']:
            price = float(instance['SpotPrice'])
            if price < minimum_price:
                minimum_price = price
                is_instance_type = True

        prices = []
        # if we found something,
        # we get all the instance types with that price
        if is_instance_type:
            for instance in response['SpotPriceHistory']:
                price = float(instance['SpotPrice'])
                if price == minimum_price:
                    instance_type = instance['InstanceType']
                    availability_zone = instance['AvailabilityZone']
                    prices.append((instance_type, price, availability_zone))
        return prices
    else:
        return []


def format_price_answer(spot_prices):
    """
    Receive a list of tuples [(price, availability-zone)]
    Return a string
    """
    prices = ""
    for price in spot_prices:
        prices += ("\n*{}$* per hour in {}".format(*price))
    return prices


def format_cheapest_answer(spot_prices_result, amazon_region, memory, cpu):
    """
    spot_prices_result is a list of tuples:
    [(instance_type, price, availability-zone)]
    Return a string
    """
    message = (
        'The cheapest instances in {} with at least {} GB of memory and {} '
        'CPUs are currently at *{}$* per hour. The instance types are:'
        '\n'.format(amazon_region, memory, cpu, spot_prices_result[0][1])
    )
    instances = ""
    for instance in spot_prices_result:
        instance_type = instance[0]
        availability_zone = instance[2]
        cores, memory = INSTANCE_TYPES.get(instance_type)
        instances += (
            '{} ({} vCPUs, {} GB in {})'
            '\n'.format(instance_type, cores, memory, availability_zone)
        )
    message += instances
    return message


def format_instance_types_answer(instances, memory, cpu):
    """
    We receive a list of instances and
    the minimum memory and CPU that the user required
    Return a string
    """
    message = (
        'The instance types with at least {} GB of memory and {} CPUs are: '
        '\n'.format(memory, cpu)
    )
    formatted_instances = ''
    # we sort the instance types for more readability
    instances.sort()
    for instance in instances:
        cores, memory = INSTANCE_TYPES.get(instance)
        formatted_instances += (
            '{} ({} vCPUs, {} GB) \n'.format(instance, cores, memory))
    message += formatted_instances
    return message


""" --- Functions that control the bot's behavior --- """


def get_current_spot_price(intent_request):
    """
    Performs dialog management and fulfillment for getting current spot price.
    """
    logger.debug('Current Intent: {}'.format(intent_request['currentIntent']))
    current = intent_request.get('currentIntent')
    slots = current.get('slots') if current else None
    instance_type = slots.get('InstanceType') if slots else None
    amazon_region = slots.get('AmazonRegion') if slots else None
    if intent_request.get('sessionAttributes'):
        session_attributes = intent_request['sessionAttributes']
    else:
        session_attributes = {}

    if intent_request['invocationSource'] == 'DialogCodeHook':
        # Validate any slots which have been specified.  If any are invalid,
        # re-elicit for their value
        validation_result = validate_get_current_spot_price(slots)
        if not validation_result['isValid']:
            slots[validation_result['violatedSlot']] = None
            return elicit_slot(
                session_attributes,
                current['name'],
                slots,
                validation_result['violatedSlot'],
                validation_result['message']
            )

        # Otherwise, let native DM rules determine how to elicit for slots
        # and/or drive confirmation.
        return delegate(session_attributes, slots)

    # Display value. Call backend
    # We get the info and we format the answer
    spot_prices_result = get_price_history([instance_type], amazon_region)
    spot_prices_message = format_price_answer(spot_prices_result)

    message = (
        'The current spot price for a {} instance in {} is {}'
        '.'.format(instance_type, amazon_region, spot_prices_message)
    )
    logger.debug(message)
    return close(
        session_attributes,
        'Fulfilled',
        {
            'contentType': 'PlainText',
            'content': message
        }
    )


def get_cheapest_spot_price(intent_request):
    """
    Performs dialog management and fulfillment for getting cheapest spot
    instance given a minimum memory and CPU.
    """
    logger.debug('Current Intent: {}'.format(intent_request['currentIntent']))
    current = intent_request.get('currentIntent')
    slots = current.get('slots') if current else None
    amazon_region = slots.get('AmazonRegion') if slots else None
    if intent_request.get('sessionAttributes'):
        session_attributes = intent_request['sessionAttributes']
    else:
        session_attributes = {}

    if intent_request['invocationSource'] == 'DialogCodeHook':
        # Validate any slots which have been specified.  If any are invalid,
        # re-elicit for their value
        validation_result = validate_get_cheapest_spot_price(slots)
        if not validation_result['isValid']:
            slots[validation_result['violatedSlot']] = None
            return elicit_slot(
                session_attributes,
                current['name'],
                slots,
                validation_result['violatedSlot'],
                validation_result['message']
            )

        # Otherwise, let native DM rules determine how to elicit for slots
        # and/or drive confirmation.
        return delegate(session_attributes, slots)

    # # Display value. Call backend
    # We get the info and we format the answer

    # first we format the inputs
    cpu = slots.get('CPUs') if slots.get('CPUs') else '1'

    if not slots.get('Memory') or not slots.get('Memory')[0].isdigit():
        memory = '0'
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

    instances = get_instances(cpu, memory)
    spot_prices_result = get_cheapest_instance(instances, amazon_region)

    if not spot_prices_result:
        message = (
            "Sorry, we couldn't find instances available in {} with at least "
            "{} GB of memory and {} CPUs.".format(amazon_region, memory, cpu)
        )
    else:
        message = format_cheapest_answer(spot_prices_result, amazon_region,
                                         memory, cpu)

    logger.debug(message)
    return close(
        session_attributes,
        'Fulfilled',
        {
            'contentType': 'PlainText',
            'content': message
        }
    )


def get_instance_types(intent_request):
    """
    Performs dialog management and fulfillment for getting instance
    types given a minimum memory and CPU.
    """
    logger.debug('Current Intent: {}'.format(intent_request['currentIntent']))
    current = intent_request.get('currentIntent')
    slots = current.get('slots') if current else None
    if intent_request.get('sessionAttributes'):
        session_attributes = intent_request['sessionAttributes']
    else:
        session_attributes = {}

    if intent_request['invocationSource'] == 'DialogCodeHook':
        # Validate any slots which have been specified.  If any are invalid,
        # re-elicit for their value
        validation_result = validate_get_instance_types(slots)
        if not validation_result['isValid']:
            slots[validation_result['violatedSlot']] = None
            return elicit_slot(
                session_attributes,
                current['name'],
                slots,
                validation_result['violatedSlot'],
                validation_result['message']
            )

        # Otherwise, let native DM rules determine how to elicit for slots
        # and/or drive confirmation.
        return delegate(session_attributes, slots)

    # # Display value. Call backend
    # We get the info and we format the answer

    # first we format the inputs
    cpu = slots.get('CPUs') if slots.get('CPUs') else '1'

    if not slots.get('Memory') or not slots.get('Memory')[0].isdigit():
        memory = '0'
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

    instances = get_instances(cpu, memory)

    if not instances:
        message = (
            "Sorry, we couldn't find instances available "
            "with at least {} GB of memory and {} CPUs.".format(memory, cpu)
        )
    else:
        message = format_instance_types_answer(instances, memory, cpu)

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

    user_id = intent_request['userId']
    intent_name = intent_request['currentIntent']['name']
    log_message = (
        'dispatch userId={}, intentName={}'.format(user_id, intent_name)
    )
    logger.debug(log_message)

    intent_name = intent_request['currentIntent']['name']

    # Dispatch to your bot's intent handlers
    if intent_name == 'GetCurrentSpotInstancePrice':
        return get_current_spot_price(intent_request)
    elif intent_name == 'GetCheapestSpotInstancesWithAtLeast':
        return get_cheapest_spot_price(intent_request)
    elif intent_name == 'GetInstanceTypes':
        return get_instance_types(intent_request)

    raise Exception('Intent with name ' + intent_name + ' not supported')


# --- Main handler ---


def lambda_handler(event, context):
    """
    Route the incoming request based on intent.
    The JSON body of the request is provided in the event slot.
    """
    logger.debug('event.bot.name={}'.format(event['bot']['name']))

    return dispatch(event)
