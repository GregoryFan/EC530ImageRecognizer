#Responsible for calling for images and embeddings from the database,
# and for inserting new images and embeddings into the database.

#Listens for the inference system to publish new embeddings, and stores them in the database.
#Listens for the vector database to query for similar images, and retrieves the relevant embeddings from the 
# database to return the results.

def upload_image(image_data):
    # Code to upload the image data to the database
    pass

def query_image(image_id):
    # Code to query the database given image ID 
    pass