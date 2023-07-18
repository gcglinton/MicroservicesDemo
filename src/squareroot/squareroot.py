import os
import json
import math
import psycopg2
import logging
from sys import stdout
from confluent_kafka import Consumer, Producer

class SqrtMicroservice:
    def __init__(self):

        # Check if required environment variables are set
        required_env_vars = ['STAGE_NUMBER', 'DB_NAME', 'DB_USER', 'DB_PASSWORD', 'INPUT_TOPIC', 'OUTPUT_TOPIC']
        missing_vars = [var for var in required_env_vars if not os.environ.get(var)]
        if missing_vars:
            self.logger.critical(f"Missing required environment variables: {', '.join(missing_vars)}")
            exit(1)
        
        self.stage = os.environ.get('STAGE_NUMBER')
        self.bootstrap_servers = os.environ.get('BOOTSTRAP_SERVERS', 'localhost:9092')
        self.input_topic = os.environ.get('INPUT_TOPIC')
        self.output_topic = os.environ.get('OUTPUT_TOPIC')
        self.db_host = os.environ.get('DB_HOST', 'localhost')
        self.db_port = os.environ.get('DB_PORT', '5432')
        self.db_name = os.environ.get('DB_NAME')
        self.db_user = os.environ.get('DB_USER')
        self.db_password = os.environ.get('DB_PASSWORD')
        self.consumer = None
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
        # Create a Kafka consumer
        self.consumer = Consumer({
            'bootstrap.servers': self.bootstrap_servers,
            'group.id': 'sqrt_microservice'
        })
        self.consumer.subscribe([self.input_topic])

        # Create a Kafka producer
        self.producer = Producer({'bootstrap.servers': self.bootstrap_servers})

        # Start consuming messages
        while True:
            message = self.consumer.poll(1.0)

            if message is None:
                continue

            if message.error():
                self.logger.critical(f"Consumer error: {message.error()}")
                continue
            
            self.logger.debug("Got message from Kafka: %s" % (message.value()))
            # Process the received message
            data = self.deserialize_message(message.value())

            data['sqrt'] = {}
            for i in ['lcm', 'sum', 'product', 'average']:
                data['sqrt'][i] = math.sqrt(data[i])

            # Save the result to the Postgres table
            self.insert_into_postgres(data['numbers'], data['sqrt'])

            # Publish the updated JSON object to the output topic
            self.publish_result(data)

    def deserialize_message(self, message):
        # Deserialize JSON message
        return json.loads(message)

    def insert_into_postgres(self, numbers, data):
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
            CREATE TABLE IF NOT EXISTS results (
                numbers TEXT,
                stage TEXT,
                result TEXT
            )
        """
        cursor.execute(create_table_query)

        # Insert the result into the table
        cursor.execute(f"INSERT INTO results (numbers, stage, result) VALUES (%s, %s, %s)", (json.dumps(numbers), self.stage, json.dumps(data)))
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
        self.logger.debug("Produce message on topic %s" % (self.output_topic))

        # Flush the producer tomake sure the message is sent
        self.producer.flush()

if __name__ == '__main__':
    microservice = SqrtMicroservice()

    microservice.start()
