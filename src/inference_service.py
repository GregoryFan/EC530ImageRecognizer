#Generates inferences, which is defined by the following:

#An inference is a boundary where an object is detected.
#[vertices, defined as (x,y) coordinates] and label, which is a string.
#An image may have multiple inferences.

#Implementation is not done in this project but estimated with dummy code.

#Listens for the Upload Service when it sends image data over.
#Publishes the inference data as the following, in JSON format.
#{
#   "image_id": "unique_image_identifier",
#   "image": image_data,  # This could be a base64 string or a file path
#    "inferences": [
#        {
#            "label": "object_label",
#            "vertices": [(x1, y1), (x2, y2),
#                         (x3, y3), (x4, y4)]
#        },
#        ...
#    ]
#}


def generate_inferences(image_data):
    pass

