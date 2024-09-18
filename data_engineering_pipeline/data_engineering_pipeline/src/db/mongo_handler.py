from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, PyMongoError
from typing import Any, Dict, Optional, List
import logging
from config import MONGO_URI, MONGO_DB_NAME, MONGO_COLLECTION_NAME

class MongoHandler:
    def __init__(self):
        self.client = None
        self.db = None
        self.collection = None

    def connect(self):
        try:
            self.client = MongoClient(MONGO_URI)
            self.db = self.client[MONGO_DB_NAME]
            self.collection = self.db[MONGO_COLLECTION_NAME]
            # The ismaster command is cheap and does not require auth.
            self.client.admin.command('ismaster')
            logging.info("Successfully connected to MongoDB")
        except ConnectionFailure:
            logging.error("Failed to connect to MongoDB")
            raise

    def close(self):
        if self.client:
            self.client.close()
            logging.info("Closed MongoDB connection")

    def save_blog_post(self, blog_content: Dict[str, Any]) -> str:
        try:
            result = self.collection.insert_one(blog_content)
            logging.info(f"Inserted document with ID: {result.inserted_id}")
            return str(result.inserted_id)
        except PyMongoError as e:
            logging.error(f"Error saving blog post to MongoDB: {e}")
            raise

    def get_all_urls(self) -> List[str]:
        try:
            return [doc['url'] for doc in self.collection.find({}, {'url': 1})]
        except PyMongoError as e:
            logging.error(f"Error retrieving URLs from MongoDB: {e}")
            raise

    def test_connection(self):
        try:
            total_documents = self.collection.count_documents({})
            logging.info(f"Total documents in collection: {total_documents}")
            if total_documents > 0:
                sample_document = self.collection.find_one()
                logging.info("Sample document:")
                logging.info(sample_document)
            else:
                logging.info("No documents found in the collection.")
        except PyMongoError as e:
            logging.error(f"Error testing MongoDB connection: {e}")
            raise