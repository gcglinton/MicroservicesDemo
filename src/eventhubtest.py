import logging
import os
from sys import stdout
from confluent_kafka import Consumer, Producer, KafkaException, KafkaError
import sys, time
from datetime import datetime

import pprint
pretty = pprint.PrettyPrinter(indent=2, width=200).pprint

# Define logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG) # set logger level
logFormatter = logging.Formatter("%(asctime)s %(message)s")
consoleHandler = logging.StreamHandler(stdout) #set streamhandler to stdout
consoleHandler.setFormatter(logFormatter)
logger.addHandler(consoleHandler)

# Check if required environment variables are set
required_env_vars = ['BOOTSTRAP_SERVERS']
missing_vars = [var for var in required_env_vars if not os.environ.get(var)]
if missing_vars:
    logger.critical(f"Missing required environment variables: {', '.join(missing_vars)}")
    exit(1)


bootstrap_servers = os.environ.get('BOOTSTRAP_SERVERS')
consumer = None
producer = None

consumer_config = {
    'bootstrap.servers': bootstrap_servers,
    'group.id': 'eventhubtest-consumer',
    'client.id': 'eventhubtest-consumer',
}
producer_config = {
    'bootstrap.servers': bootstrap_servers,
    'client.id': 'eventhubtest-producer',
}

#Make it so we can use Azure Event Hub.
if 'servicebus.windows.net' in bootstrap_servers:
    # required_env_vars = ['EVENTHUB_USERNAME', 'EVENTHUB_CONNECTIONSTRING']
    # missing_vars = [var for var in required_env_vars if not os.environ.get(var)]
    # if missing_vars:
    #     logger.critical(f"Missing required environment variables: {', '.join(missing_vars)}")
    #     exit(1)

    producer_config['security.protocol'] = consumer_config['security.protocol'] = 'SASL_SSL'
    producer_config['sasl.mechanism'] = consumer_config['sasl.mechanism'] = 'PLAIN'
    #producer_config['sasl.username'] = consumer_config['sasl.username'] = os.getenv('EVENTHUB_USERNAME')
    #producer_config['sasl.password'] = consumer_config['sasl.password'] = os.getenv('EVENTHUB_CONNECTIONSTRING')
    producer_config['sasl.username'] = consumer_config['sasl.username'] = '$ConnectionString'
    cs = 'Endpoint=sb://microservicetest.servicebus.windows.net/;SharedAccessKeyName=RootManageSharedAccessKey;SharedAccessKey=mGjDllPwCpqKqzXiS2QDSuyc2OnnSE6/g+AEhEGH6B4='
    producer_config['sasl.password'] = consumer_config['sasl.password'] = cs

    #consumer_config['default.topic.config'] = {'auto.offset.reset': 'latest'}
    #consumer_config['request.timeout.ms'] = 60000
    consumer_config['session.timeout.ms'] = 60000



# # Create a Kafka producer
# producer = Producer(producer_config)

# def _acked(err, msg):
#         if err is not None:
#             logger.error("Failed to deliver message on topic %s; %s" % (str(msg.topic()), str(err)))
#         else:
#             logger.debug("Message produced on topic %s in %.3fs: %s"  % (str(msg.topic()), msg.latency(), msg.value().decode("utf-8")))


# def post(value, destination):
#     producer.produce(destination, value=value, callback=_acked)

#     # Wait up to 1 second for events. Callbacks will be invoked during
#     # this method call if the message is acknowledged.
#     producer.flush()

def get_many():

    ret = []
    for msg in consumer.consume(num_messages=10,  timeout=10.0, ):
        if msg.error():
            # Error or event
            if msg.error().code() == KafkaError._PARTITION_EOF:
                # End of partition event
                logger.debug('%% %s [%d] reached end at offset %d\n' %
                                    (msg.topic(), msg.partition(), msg.offset()))
            else:
                # Error
                logger.debug(msg.error())
        else:
            # Proper message
            ret.append(msg.value())

    #consumer.commit()
    return ret

def get_one():
    msg = consumer.poll(timeout=10.0)
    if msg is None:
        return None

    if msg.error():
        # Error or event
        if msg.error().code() == KafkaError._PARTITION_EOF:
            # End of partition event
            logger.debug('%% %s [%d] reached end at offset %d\n' %
                                (msg.topic(), msg.partition(), msg.offset()))
        else:
            # Error
            logger.debug(msg.error())
    else:
        # Proper message
        #consumer.commit()
        return msg.value()

def now():
    return datetime.utcnow().isoformat(sep='T', timespec='milliseconds')

def print_assignment(c, partitions):
    print('Assignment:', partitions)

def print_revoke(c, partitions):
    print('Revoke:', partitions)

def print_lost(c, partitions):
    print('Lost:', partitions)





# post("foobar1-1__" + now(), "topic1")
# post("foobar1-2__" + now(), "topic1")
# post("foobar1-3__" + now(), "topic1")
# post("foobar1-4__" + now(), "topic1")
# post("foobar2-1__" + now(), "topic2")
# post("foobar2-2__" + now(), "topic2")
# post("foobar2-3__" + now(), "topic2")
# post("foobar1-5__" + now(), "topic1")
# post("foobar1-6__" + now(), "topic1")
# post("foobar1-7__" + now(), "topic1")
# post("foobar1-8__" + now(), "topic1")


# Create a Kafka consumer
consumer = Consumer(consumer_config)

consumer.subscribe(["topic1", "topic2"], on_assign=print_assignment, on_revoke=print_revoke, on_lost=print_lost)

try:
    while True:
        #print("get_many()")
        #pretty(get_many())

        print("get_one()")
        pretty(get_one())

except KeyboardInterrupt:
        sys.stderr.write('%% Aborted by user\n')

finally:
    # Close down consumer to commit final offsets.

    consumer.commit()
    consumer.close()