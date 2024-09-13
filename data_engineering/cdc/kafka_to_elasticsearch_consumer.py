from kafka import KafkaConsumer
from elasticsearch import Elasticsearch
import json

# Kafka Consumer
consumer = KafkaConsumer(
    'dbserver1.web_scraper_db.blog_posts',
    bootstrap_servers=['localhost:9092'],
    auto_offset_reset='earliest',
    enable_auto_commit=True,
    group_id='my-group',
    value_deserializer=lambda x: json.loads(x.decode('utf-8'))
)

# Elasticsearch connection
es = Elasticsearch(['http://localhost:9200'])

def process_message(message):
    # Extract relevant information from the Debezium message
    operation = message['payload']['op']
    document_id = str(message['payload']['after']['_id'])
    document = message['payload']['after']

    if operation in ('c', 'r', 'u'):  # Create, Read, or Update operations
        # Index the document in Elasticsearch
        es.index(index='blog_posts', id=document_id, body=document)
    elif operation == 'd':  # Delete operation
        # Delete the document from Elasticsearch
        es.delete(index='blog_posts', id=document_id)

# Main loop
for message in consumer:
    process_message(message.value)