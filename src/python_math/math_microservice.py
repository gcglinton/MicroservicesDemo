import os
import json
import psycopg2
from confluent_kafka import Consumer, Producer

class SumOperation:
    def calculate(self, numbers):
        return sum(numbers)

class MultiplyOperation:
    def calculate(self, numbers):
        result = 1
        for num in numbers:
            result *= num
        return result

class MathMicroservice:
    def __init__(self):

        # Check if required environment variables are set
        required_env_vars = ['OPERATION_TYPE', 'DB_NAME', 'DB_USER', 'DB_PASSWORD']
        missing_vars = [var for var in required_env_vars if not os.environ.get(var)]
        if missing_vars:
            print(f"Missing required environment variables: {', '.join(missing_vars)}")
            exit(1)
        self.bootstrap_servers = os.environ.get('BOOTSTRAP_SERVERS', 'localhost:9092')
        self.input_topic = os.environ.get('INPUT_TOPIC', 'input_topic')
        self.output_topic = os.environ.get('OUTPUT_TOPIC', 'output_topic')
        self.db_host = os.environ.get('DB_HOST', 'localhost')
        self.db_port = os.environ.get('DB_PORT', '5432')
        self.db_name = os.environ.get('DB_NAME')
        self.db_user = os.environ.get('DB_USER')
        self.db_password = os.environ.get('DB_PASSWORD')
        self.operation = self.get_operation()
        self.consumer = None
        self.producer = None
        
        #self.operation_name = 'sum' if isinstance(self.operation, SumOperation) else 'product'
        #self.stage = 'stage1' if self.operation_name == 'sum' else 

    def get_operation(self):
        operation_type = os.environ.get('OPERATION_TYPE')
        if operation_type == 'add':
            self.stage = 'stage1'
            self.operation_name = 'sum'
            return SumOperation()
        elif operation_type == 'multiply':
            self.stage = 'stage2'
            self.operation_name = 'product'
            return MultiplyOperation()
        else:
            print(f"Invalid OPERATION_TYPE; must be 'add', or 'multiply'")
            exit(1)

    def start(self):
        # Create a Kafka consumer
        self.consumer = Consumer({
            'bootstrap.servers': self.bootstrap_servers,
            'group.id': self.operation_name + '_microservice'
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
                print(f"Consumer error: {message.error()}")
                continue

            # Process the received message
            data = self.deserialize_message(message.value())
            numbers = data['numbers']
            result = self.operation.calculate(numbers)

            # Add the result to the input JSON object with a dynamic key name
            
            data[self.operation_name] = result

            # Save the result to the Postgres table
            self.insert_into_postgres(data)

            # Publish the updated JSON object to the output topic
            self.publish_result(data)

    def deserialize_message(self, message):
        # Deserialize JSON message
        return json.loads(message)

    def insert_into_postgres(self, data):
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
        cursor.execute(f"INSERT INTO results (numbers, stage, result) VALUES (%s, %s, %s)", (json.dumps(data['numbers']), self.stage, data[self.operation_name]))

        # Commit the transaction and close the connection
        conn.commit()
        cursor.close()
        conn.close()

    def publish_result(self, data):
        # Serialize JSON object
        payload = json.dumps(data)

        # Publish the result to the output topic
        self.producer.produce(self.output_topic, value=payload.encode('utf-8'))

        # Flush the producer tomake sure the message is sent
        self.producer.flush()


if __name__ == '__main__':
    microservice = MathMicroservice()

    microservice.start()
