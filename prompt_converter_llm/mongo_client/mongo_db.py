from pymongo import MongoClient
import logging as log
import certifi
import time

class Mongo_Db:
    """
    A helper class to manage interactions with a MongoDB database,
    including connection, CRUD operations, and cleanup. Except Update
    """
    def __init__(self,user,password,mongo_url):
        self.password = password
        self.user = user
        self.mongo_url = mongo_url
        self.client = None
        
        try:
            url = f"mongodb+srv://{self.user}:{self.password}{self.mongo_url}"
            self.client = MongoClient(url,tlsCAFile=certifi.where())
            
            # Send a ping to confirm a successful connection
            self.client.admin.command('ping')
            log.info("MongoDB connection successful. ✅")
            
        except Exception as e:
            log.error(f"Error Connecting to Database: {e}")
            raise ConnectionError("Failed to connect to MongoDB.") from e
    
    def find_documents(self, database, collection, query={}, limit=0):
        """
        Finds documents in a collection based on a query.
        Returns a list of documents.
        """
        tries = 0
        while tries < 5:
            try:
                db = self.client.get_database(database)
                collection_obj = db.get_collection(collection)
                cursor = collection_obj.find(query)
                
                if limit > 0:
                    cursor = cursor.limit(limit)
                
                return list(cursor)
            
            except Exception as e:
                log.error(f"Error finding documents: {e}")
                tries += 1
                time.sleep(3)
        return []
    
    
    def push(self,database,collection,data_to_push):
        """
        Pushes a single document (dict) or multiple documents (list of dicts).
        Returns the inserted ID(s) or None on failure.
        """
        
        tries=0
        while tries < 5:
            try:
                db = self.client.get_database(f"{database}")
                collection_name = db.get_collection(f"{collection}")
            
                ## Checking if the data to be pushed is a list or a dictionary
                if isinstance(data_to_push,list):
                    if not data_to_push:
                        log.warning("The provided list is empty. No documents to insert.")
                        return None
                    
                    results = collection_name.insert_many(data_to_push)
                    log.info(f"Inserted {len(results.inserted_ids)} documents.")
                    return results.inserted_ids
                else:
                    results = collection_name.insert_one(data_to_push)
                    log.info(f"Inserted a document with the _id: {results.inserted_id}")
                    
                    return results.inserted_id
            
            except Exception as e:
                tries += 1
                log.error(f"Error inserting document (Attempt {tries}/6): {e}")
                time.sleep(3)
                
        return None
    
    def update(self,database,collection,primary_field,unique_key,updated_fields):
        """
        Updating an Existing Document in MongoDB
        """
        tries,maximum = 1,5
        while tries <= maximum:
            try:
                db = self.client.get_database(database)
                collection_name = db.get_collection(collection)
                
                query_filter = {primary_field:unique_key}
                update_operation = {'$set': updated_fields
                    }
                
                result = collection_name.update_one(query_filter,update_operation)

                if result.matched_count > 0 and result.modified_count > 0:
                    log.info(f"Document {unique_key} updated successfully.")
                    return True
                else:
                    log.warning(f"No matching document or no changes made for {unique_key}.")
                return False
                            
            except Exception as e:
                tries += 1
                log.error(f"Error updating document (Attempt {tries}/5): {e}")
                time.sleep(3)
                
        return None
                
    
    def delete_collection(self,database,collection):
        """Deletes an entire collection with a retry mechanism."""
        tries = 0
        while tries < 5:
            try:
                db = self.client.get_database(f"{database}")
                collection_name = db.get_collection(f"{collection}")
                collection_name.drop()
                
                log.info(f"Collection '{collection}' deleted successfully from database '{database}'.")
                
                return
            
            except Exception as e:
                log.error(f"Error deleting collection: {e}")
                tries += 1
                time.sleep(3)
                
    def delete_database(self,database):
        """Deletes an entire database with a retry mechanism."""
        tries = 0
        while tries < 5:
            try:
                self.client.drop_database(database)
                log.info(f"Database: '{database}' deleted successfully.")
                
                return
            
            except Exception as e:
                log.error(f"Error deleting collection: {e}")
                tries += 1
                time.sleep(3)
                
    def clean_mongodoc(self,doc):
        if "_id" in doc:
            doc["_id"] = str(doc["_id"])
        
        return doc
    
    def close_connection(self):
        """Closes the MongoDB client connection."""

        self.client.close()
        log.info("MongoDB connection closed. ✅")
        
    def __enter__(self):
        """Allows the class to be used in a 'with' statement."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Ensures the connection is closed when exiting the 'with' block."""
        self.close_connection()
