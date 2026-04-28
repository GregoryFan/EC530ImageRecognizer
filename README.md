# EC530ImageRetrievalSystem

## This is a hypothetical Image Retrieval System that would use machine learning to generate embeddings and predict inferences in order to retrieve them later via searching by general tag.

## The system uses a pub-sub architecture, and each component can be activated one at a time as long as `start()` is called for each of them. Alternatively, running `main.py` starts all services concurrently for ease of use.

## To run tests, run pytest on the root repository. Note that general tests are made as machiine learning components do not exist.

### Main Components:

`upload_service`: The upload service takes in image paths that the user gives and attempts to open and store the file in the form of a base64 format. It then publishes the metadata alongside the image data to hopefully be received by the inference service.

`inference_service`: The inference service generates inferences (which are denoted by a tag, followed by vertices around the supposed topic the tag defines) for a given image. This is typically done with a machine learning model, but this project leaves temporary code instead as a proof of concept. The inference service publishes the inferences alongside the image and meta data over to hopefully be received by the document database and embedding service.

`db_service`: The Document Database is a mongodb server that stores image data alongside their inferences. This is called upon when the user attempts to query for a stored image.

`embedding_service`: The embedding service attempts to generate embeddings for a given inference. This is typically done with a machine learning model, but again this is not included in this project so temporary code is substituted instead. This is then passed to the vector database for storage.

`vector_db`: The vector database stores embeddings through FAISS while keeping metadata in another mongodb server, When queried, the database will search via FAISS through closest distance embeddings and give images when deemed similar enough.

`main`: This is the CLI of the project, it sends the user inputs over to the vector database or upload service.



