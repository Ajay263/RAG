1. ## Run the file

`python db.py`


2. ### Check thje data in the database

`docker ps`

3. ### access the MongoDB shel

`docker exec -it 1ec6f2de4694 mongosh -u root -p root`


4. ### Once inside the MongoDB shell,  verify the data 

`

show dbs

use your_database_name

db.your_collection_name.find()





`
