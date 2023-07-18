import os
import json
import random
import time
import psycopg2
import logging
from sys import stdout
from confluent_kafka import Consumer, Producer

class NumberGeneratorMicroservice:
    def __init__(self):

        # Check if required environment variables are set
        required_env_vars = ['STAGE_NUMBER', 'DB_NAME', 'DB_USER', 'DB_PASSWORD', 'OUTPUT_TOPIC']
        missing_vars = [var for var in required_env_vars if not os.environ.get(var)]
        if missing_vars:
            print(f"Missing required environment variables: {', '.join(missing_vars)}")
            exit(1)

        self.stage = os.environ.get('STAGE_NUMBER')
        self.bootstrap_servers = os.environ.get('BOOTSTRAP_SERVERS', 'localhost:9092')
        self.output_topic = os.environ.get('OUTPUT_TOPIC')
        self.message_min = os.environ.get('MESSAGE_MIN', 1)
        self.message_max = os.environ.get('MESSAGE_MAX', 20)
        self.sleep_min = float(os.environ.get('SLEEP_MIN', 1))
        self.sleep_max = float(os.environ.get('SLEEP_MAX', 10))
        self.numbers_min = float(os.environ.get('NUMBERS_MIN', 1000))
        self.numbers_max = float(os.environ.get('NUMBERS_MAX', 100000))
        self.count_min = os.environ.get('COUNT_MIN', 3)
        self.count_max = os.environ.get('COUNT_MAX', 20)
        self.db_host = os.environ.get('DB_HOST', 'localhost')
        self.db_port = os.environ.get('DB_PORT', '5432')
        self.db_name = os.environ.get('DB_NAME')
        self.db_user = os.environ.get('DB_USER')
        self.db_password = os.environ.get('DB_PASSWORD')

        self.producer = None

        # Define logger
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG) # set logger level
        logFormatter = logging.Formatter\
        ("%(asctime)s %(message)s")
        consoleHandler = logging.StreamHandler(stdout) #set streamhandler to stdout
        consoleHandler.setFormatter(logFormatter)
        self.logger.addHandler(consoleHandler)


    def start(self):
        # Create a Kafka producer
        self.producer = Producer({'bootstrap.servers': self.bootstrap_servers})

        # Start consuming messages
        while True:

            rand_sleep = random.uniform(self.sleep_min , self.sleep_max)
            self.logger.debug("Sleeping %d seconds" %(rand_sleep))
            time.sleep(rand_sleep)

            
            message_count = random.randint(self.message_min, self.message_max)
            self.logger.debug("generating %d messages" %(message_count))
            for _ in range(message_count): 
                number_count = random.randint(self.count_min, self.count_max)
                self.logger.debug("generating %d numbers" %(number_count))
                data = {'numbers': []}
                for _ in range(number_count):
                    data['numbers'].append(random.uniform(self.numbers_min, self.numbers_max))

                # Save the result to the Postgres table
                self.insert_into_postgres(data['numbers'])

                # Publish the updated JSON object to the output topic
                self.publish_result(data)

    def insert_into_postgres(self, numbers):
        # Connect to the Postgres database
        conn = psycopg2.connect(
            host=self.db_host,
            port=self.db_port,
            dbname=self.db_name,
            user=self.db_user,
            password=self.db_password
        )
        cursor = conn.cursor()
        create_table_query = """
            CREATE TABLE IF NOT EXISTS inputs (
                numbers TEXT,
                dt timestamp 
            )
        """
        cursor.execute(create_table_query)

        # Insert the result into the table
        cursor.execute(f"INSERT INTO inputs (numbers, dt) VALUES ('{json.dumps(numbers)}', now())")
        self.logger.debug("SQL Query: " + str(cursor.query))

        # Commit the transaction and close the connection
        conn.commit()
        cursor.close()
        conn.close()

    def publish_result(self, data):
        # Serialize JSON object
        payload = json.dumps(data)

        # Publish the result to the output topic
        self.producer.produce(self.output_topic, value=payload.encode('utf-8'))
        self.logger.debug("Produce message on topic '%s': %s" % (self.output_topic, payload))

        # Flush the producer tomake sure the message is sent
        self.producer.flush()

if __name__ == '__main__':
    microservice = NumberGeneratorMicroservice()

    microservice.start()
