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


def confirm_intent(session_attributes, intent_name, slots, message):
    return {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'ConfirmIntent',
            'intentName': intent_name,
            'slots': slots,
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


def safe_int(n):
    """
    Safely convert n value to int.
    """
    if n is not None:
        return int(n)
    return n


def try_ex(func):
    """
    Call passed in function in try block. If KeyError is encountered return None.
    This function is intended to be used to safely access dictionary.

    Note that this function would have negative impact on performance.
    """

    try:
        return func()
    except KeyError:
        return None


def generate_car_price(location, days, age, car_type):
    """
    Generates a number within a reasonable range that might be expected for a flight.
    The price is fixed for a given pair of locations.
    """

    car_types = ['economy', 'standard', 'midsize', 'full size', 'minivan', 'luxury']
    base_location_cost = 0
    for i in range(len(location)):
        base_location_cost += ord(location.lower()[i]) - 97

    age_multiplier = 1.10 if age < 25 else 1
    # Select economy is car_type is not found
    if car_type not in car_types:
        car_type = car_types[0]

    return days * ((100 + base_location_cost) + ((car_types.index(car_type.lower()) * 50) * age_multiplier))


def generate_hotel_price(location, nights, room_type):
    """
    Generates a number within a reasonable range that might be expected for a hotel.
    The price is fixed for a pair of location and roomType.
    """

    room_types = ['queen', 'king', 'deluxe']
    cost_of_living = 0
    for i in range(len(location)):
        cost_of_living += ord(location.lower()[i]) - 97

    return nights * (100 + cost_of_living + (100 + room_types.index(room_type.lower())))


def isvalid_car_type(car_type):
    car_types = ['economy', 'standard', 'midsize', 'full size', 'minivan', 'luxury']
    return car_type.lower() in car_types


def isvalid_city(city):
    valid_cities = ['new york', 'los angeles', 'chicago', 'houston', 'philadelphia', 'phoenix', 'san antonio',
                    'san diego', 'dallas', 'san jose', 'austin', 'jacksonville', 'san francisco', 'indianapolis',
                    'columbus', 'fort worth', 'charlotte', 'detroit', 'el paso', 'seattle', 'denver', 'washington dc',
                    'memphis', 'boston', 'nashville', 'baltimore', 'portland']
    return city.lower() in valid_cities


def isvalid_room_type(room_type):
    room_types = ['queen', 'king', 'deluxe']
    return room_type.lower() in room_types


def isvalid_date(date):
    try:
        dateutil.parser.parse(date)
        return True
    except ValueError:
        return False


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

def get_day_difference(later_date, earlier_date):
    later_datetime = dateutil.parser.parse(later_date).date()
    earlier_datetime = dateutil.parser.parse(earlier_date).date()
    return abs(later_datetime - earlier_datetime).days


def add_days(date, number_of_days):
    new_date = dateutil.parser.parse(date).date()
    new_date += datetime.timedelta(days=number_of_days)
    return new_date.strftime('%Y-%m-%d')

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


def validate_book_car(slots):
    pickup_city = try_ex(lambda: slots['PickUpCity'])
    pickup_date = try_ex(lambda: slots['PickUpDate'])
    return_date = try_ex(lambda: slots['ReturnDate'])
    driver_age = safe_int(try_ex(lambda: slots['DriverAge']))
    car_type = try_ex(lambda: slots['CarType'])

    if pickup_city and not isvalid_city(pickup_city):
        return build_validation_result(
            False,
            'PickUpCity',
            'We currently do not support {} as a valid destination.  Can you try a different city?'.format(pickup_city)
        )

    if pickup_date:
        if not isvalid_date(pickup_date):
            return build_validation_result(False, 'PickUpDate', 'I did not understand your departure date.  When would you like to pick up your car rental?')
        if datetime.datetime.strptime(pickup_date, '%Y-%m-%d').date() <= datetime.date.today():
            return build_validation_result(False, 'PickUpDate', 'Reservations must be scheduled at least one day in advance.  Can you try a different date?')

    if return_date:
        if not isvalid_date(return_date):
            return build_validation_result(False, 'ReturnDate', 'I did not understand your return date.  When would you like to return your car rental?')

    if pickup_date and return_date:
        if dateutil.parser.parse(pickup_date) >= dateutil.parser.parse(return_date):
            return build_validation_result(False, 'ReturnDate', 'Your return date must be after your pick up date.  Can you try a different return date?')

        if get_day_difference(pickup_date, return_date) > 30:
            return build_validation_result(False, 'ReturnDate', 'You can reserve a car for up to thirty days.  Can you try a different return date?')

    if driver_age is not None and driver_age < 18:
        return build_validation_result(
            False,
            'DriverAge',
            'Your driver must be at least eighteen to rent a car.  Can you provide the age of a different driver?'
        )

    if car_type and not isvalid_car_type(car_type):
        return build_validation_result(
            False,
            'CarType',
            'I did not recognize that model.  What type of car would you like to rent?  '
            'Popular cars are economy, midsize, or luxury')

    return {'isValid': True}


def validate_hotel(slots):
    location = try_ex(lambda: slots['Location'])
    checkin_date = try_ex(lambda: slots['CheckInDate'])
    nights = safe_int(try_ex(lambda: slots['Nights']))
    room_type = try_ex(lambda: slots['RoomType'])

    if location and not isvalid_city(location):
        return build_validation_result(
            False,
            'Location',
            'We currently do not support {} as a valid destination.  Can you try a different city?'.format(location)
        )

    if checkin_date:
        if not isvalid_date(checkin_date):
            return build_validation_result(False, 'CheckInDate', 'I did not understand your check in date.  When would you like to check in?')
        if datetime.datetime.strptime(checkin_date, '%Y-%m-%d').date() <= datetime.date.today():
            return build_validation_result(False, 'CheckInDate', 'Reservations must be scheduled at least one day in advance.  Can you try a different date?')

    if nights is not None and (nights < 1 or nights > 30):
        return build_validation_result(
            False,
            'Nights',
            'You can make a reservations for from one to thirty nights.  How many nights would you like to stay for?'
        )

    if room_type and not isvalid_room_type(room_type):
        return build_validation_result(False, 'RoomType', 'I did not recognize that room type.  Would you like to stay in a queen, king, or deluxe room?')

    return {'isValid': True}

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
            price = round(float(instance['SpotPrice']), 2)
            if price < minimum_price:
                minimum_price = price
                instance_type = instance['InstanceType']
                availability_zone = instance['AvailabilityZone']

        prices = []
        # if we found something, we get the other instance types with the same price
        if instance_type:
            for instance in response['SpotPriceHistory']:
                price = round(float(instance['SpotPrice']), 2)
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
    return "\n".join("*{:.2f}$* in {}".format(*price) for price in spot_prices)


def format_cheapest_answer(spot_prices_result, amazon_region, memory, cpu):
    """
    spot_prices_result is a list of tuples [(instance_type, price, availability-zone)]
    Return a string
    """
    message = 'The cheapest instances in {} with at least {} GB of memory and {} CPUs are currently at *{}$*. The instance types are: \n'.format(amazon_region, memory, cpu, spot_prices_result[0][1])
    instances = ""
    for instance in spot_prices_result:
        instances += '{} ({} vCPUs, {} GB in {})\n'.format(instance[0], INSTANCE_TYPES.get(instance[0])[0], INSTANCE_TYPES.get(instance[0])[1], instance[2])
    message += instances
    return message

""" --- Functions that control the bot's behavior --- """


def book_hotel(intent_request):
    """
    Performs dialog management and fulfillment for booking a hotel.

    Beyond fulfillment, the implementation for this intent demonstrates the following:
    1) Use of elicitSlot in slot validation and re-prompting
    2) Use of sessionAttributes to pass information that can be used to guide conversation
    """
    location = try_ex(lambda: intent_request['currentIntent']['slots']['Location'])
    checkin_date = try_ex(lambda: intent_request['currentIntent']['slots']['CheckInDate'])
    nights = safe_int(try_ex(lambda: intent_request['currentIntent']['slots']['Nights']))

    room_type = try_ex(lambda: intent_request['currentIntent']['slots']['RoomType'])
    session_attributes = intent_request['sessionAttributes'] if intent_request['sessionAttributes'] is not None else {}

    # Load confirmation history and track the current reservation.
    reservation = json.dumps({
        'ReservationType': 'Hotel',
        'Location': location,
        'RoomType': room_type,
        'CheckInDate': checkin_date,
        'Nights': nights
    })

    session_attributes['currentReservation'] = reservation

    if intent_request['invocationSource'] == 'DialogCodeHook':
        # Validate any slots which have been specified.  If any are invalid, re-elicit for their value
        validation_result = validate_hotel(intent_request['currentIntent']['slots'])
        if not validation_result['isValid']:
            slots = intent_request['currentIntent']['slots']
            slots[validation_result['violatedSlot']] = None

            return elicit_slot(
                session_attributes,
                intent_request['currentIntent']['name'],
                slots,
                validation_result['violatedSlot'],
                validation_result['message']
            )

        # Otherwise, let native DM rules determine how to elicit for slots and prompt for confirmation.  Pass price
        # back in sessionAttributes once it can be calculated; otherwise clear any setting from sessionAttributes.
        if location and checkin_date and nights and room_type:
            # The price of the hotel has yet to be confirmed.
            price = generate_hotel_price(location, nights, room_type)
            session_attributes['currentReservationPrice'] = price
        else:
            try_ex(lambda: session_attributes.pop('currentReservationPrice'))

        session_attributes['currentReservation'] = reservation
        return delegate(session_attributes, intent_request['currentIntent']['slots'])

    # Booking the hotel.  In a real application, this would likely involve a call to a backend service.
    logger.debug('bookHotel under={}'.format(reservation))

    try_ex(lambda: session_attributes.pop('currentReservationPrice'))
    try_ex(lambda: session_attributes.pop('currentReservation'))
    session_attributes['lastConfirmedReservation'] = reservation

    return close(
        session_attributes,
        'Fulfilled',
        {
            'contentType': 'PlainText',
            'content': 'Thanks, I have placed your reservation.   Please let me know if you would like to book a car '
                       'rental, or another hotel.'
        }
    )


def book_car(intent_request):
    """
    Performs dialog management and fulfillment for booking a car.

    Beyond fulfillment, the implementation for this intent demonstrates the following:
    1) Use of elicitSlot in slot validation and re-prompting
    2) Use of sessionAttributes to pass information that can be used to guide conversation
    """
    slots = intent_request['currentIntent']['slots']
    pickup_city = slots['PickUpCity']
    pickup_date = slots['PickUpDate']
    return_date = slots['ReturnDate']
    driver_age = slots['DriverAge']
    car_type = slots['CarType']
    confirmation_status = intent_request['currentIntent']['confirmationStatus']
    session_attributes = intent_request['sessionAttributes'] if intent_request['sessionAttributes'] is not None else {}
    last_confirmed_reservation = try_ex(lambda: session_attributes['lastConfirmedReservation'])
    if last_confirmed_reservation:
        last_confirmed_reservation = json.loads(last_confirmed_reservation)
    confirmation_context = try_ex(lambda: session_attributes['confirmationContext'])

    # Load confirmation history and track the current reservation.
    reservation = json.dumps({
        'ReservationType': 'Car',
        'PickUpCity': pickup_city,
        'PickUpDate': pickup_date,
        'ReturnDate': return_date,
        'CarType': car_type
    })
    session_attributes['currentReservation'] = reservation

    if pickup_city and pickup_date and return_date and driver_age and car_type:
        # Generate the price of the car in case it is necessary for future steps.
        price = generate_car_price(pickup_city, get_day_difference(pickup_date, return_date), driver_age, car_type)
        session_attributes['currentReservationPrice'] = price

    if intent_request['invocationSource'] == 'DialogCodeHook':
        # Validate any slots which have been specified.  If any are invalid, re-elicit for their value
        validation_result = validate_book_car(intent_request['currentIntent']['slots'])
        if not validation_result['isValid']:
            slots[validation_result['violatedSlot']] = None
            return elicit_slot(
                session_attributes,
                intent_request['currentIntent']['name'],
                slots,
                validation_result['violatedSlot'],
                validation_result['message']
            )

        # Determine if the intent (and current slot settings) has been denied.  The messaging will be different
        # if the user is denying a reservation he initiated or an auto-populated suggestion.
        if confirmation_status == 'Denied':
            # Clear out auto-population flag for subsequent turns.
            try_ex(lambda: session_attributes.pop('confirmationContext'))
            try_ex(lambda: session_attributes.pop('currentReservation'))
            if confirmation_context == 'AutoPopulate':
                return elicit_slot(
                    session_attributes,
                    intent_request['currentIntent']['name'],
                    {
                        'PickUpCity': None,
                        'PickUpDate': None,
                        'ReturnDate': None,
                        'DriverAge': None,
                        'CarType': None
                    },
                    'PickUpCity',
                    {
                        'contentType': 'PlainText',
                        'content': 'Where would you like to make your car reservation?'
                    }
                )

            return delegate(session_attributes, intent_request['currentIntent']['slots'])

        if confirmation_status == 'None':
            # If we are currently auto-populating but have not gotten confirmation, keep requesting for confirmation.
            if (not pickup_city and not pickup_date and not return_date and not driver_age and not car_type)\
                    or confirmation_context == 'AutoPopulate':
                if last_confirmed_reservation and try_ex(lambda: last_confirmed_reservation['ReservationType']) == 'Hotel':
                    # If the user's previous reservation was a hotel - prompt for a rental with
                    # auto-populated values to match this reservation.
                    session_attributes['confirmationContext'] = 'AutoPopulate'
                    return confirm_intent(
                        session_attributes,
                        intent_request['currentIntent']['name'],
                        {
                            'PickUpCity': last_confirmed_reservation['Location'],
                            'PickUpDate': last_confirmed_reservation['CheckInDate'],
                            'ReturnDate': add_days(
                                last_confirmed_reservation['CheckInDate'], last_confirmed_reservation['Nights']
                            ),
                            'CarType': None,
                            'DriverAge': None
                        },
                        {
                            'contentType': 'PlainText',
                            'content': 'Is this car rental for your {} night stay in {} on {}?'.format(
                                last_confirmed_reservation['Nights'],
                                last_confirmed_reservation['Location'],
                                last_confirmed_reservation['CheckInDate']
                            )
                        }
                    )

            # Otherwise, let native DM rules determine how to elicit for slots and/or drive confirmation.
            return delegate(session_attributes, intent_request['currentIntent']['slots'])

        # If confirmation has occurred, continue filling any unfilled slot values or pass to fulfillment.
        if confirmation_status == 'Confirmed':
            # Remove confirmationContext from sessionAttributes so it does not confuse future requests
            try_ex(lambda: session_attributes.pop('confirmationContext'))
            if confirmation_context == 'AutoPopulate':
                if not driver_age:
                    return elicit_slot(
                        session_attributes,
                        intent_request['currentIntent']['name'],
                        intent_request['currentIntent']['slots'],
                        'DriverAge',
                        {
                            'contentType': 'PlainText',
                            'content': 'How old is the driver of this car rental?'
                        }
                    )
                elif not car_type:
                    return elicit_slot(
                        session_attributes,
                        intent_request['currentIntent']['name'],
                        intent_request['currentIntent']['slots'],
                        'CarType',
                        {
                            'contentType': 'PlainText',
                            'content': 'What type of car would you like? Popular models are '
                                       'economy, midsize, and luxury.'
                        }
                    )

            return delegate(session_attributes, intent_request['currentIntent']['slots'])

    # Booking the car.  In a real application, this would likely involve a call to a backend service.
    logger.debug('bookCar at={}'.format(reservation))
    del session_attributes['currentReservationPrice']
    del session_attributes['currentReservation']
    session_attributes['lastConfirmedReservation'] = reservation
    return close(
        session_attributes,
        'Fulfilled',
        {
            'contentType': 'PlainText',
            'content': 'Thanks, I have placed your reservation.'
        }
    )


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
