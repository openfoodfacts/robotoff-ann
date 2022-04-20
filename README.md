# Robotoff ANN

This project helps [robotoff](https://github.com/openfoodfacts/robotoff) in categorizing logos. Bug tracking is mostly [done on the main Robotoff repository](https://github.com/openfoodfacts/robotoff/issues/596)
## Tangible results
* You can see all the crops generated and up for manual annotation in [Hunger Games](https://hunger.openfoodfacts.org/logos), our gamified annotation engine.
* Robotoff pings new crops and annotations in the #robotoff-alerts-annotations Slack channel

## Contributing

To setup the project you must have a recent version of docker and docker-compose installed.

use `make dev`.

`make quality` will run linters and tests.

Models used in production are published in releases of [openfoodfacts-ai](https://github.com/openfoodfacts/openfoodfacts-ai/).

See more in Makefile.

## Architecture

From images we extract logos (logo detection is in robotoff).
Those logos are embedded in a metric space using a specific model[^embedding].

![Artist view of logo embeddings](./docs/logos-embedding.jpg)

We then use [approximate nearest neighbors](https://en.wikipedia.org/wiki/Nearest_neighbor_search#Approximate_nearest_neighbor) [^ann_index]
in this metric space
to try to classify the logos from known examples [KNN](https://en.wikipedia.org/wiki/K-nearest_neighbors_algorithm).

Those logos will then
help apply labels to [Open Food Facts](https://world.openfoodfacts.org) products.

Main entry point is [API](./api.py) to get nearest neighbors,
either for logo id [^nn_id], or an embedding vector [^nn_embedding], or add new logo from a image [^add_logo].

Note that the approximate nearest neighbors index is only regenerated using a specific command [^index_regenerate].


[^embedding]: see `embeddings.generate_embeddings`
and `settings.DEFAULT_MODEL`

[^ann_index]: see `api.ANNIndex` which currently relies on [Annoy](https://github.com/spotify/annoy/)

[^nn_id]: see `api.ANNResource` and `api.ANNBatchResource`

[^nn_embedding]: see `api.ANNEmbeddingResource`

[^add_logo]: see `api.AddLogoResource`

[^index_regenerate]: see `manage.generate_index`


### How does it work ?

* The ANN /add endpoints works as follows:
* from the raw image and detected bounding boxes, we crop the image to get all detected logos.
* Each logo is provided as input to the neural network (here an EfficientNet), to get an embedding for each logo.
* The embedding is saved locally on an HDF5 file (https://github.com/openfoodfacts/robotoff-ann/blob/6abaee7ec187587556431d96ed97ea71be0ad848/embeddings.py#L72).


### Annotation
* https://wiki.openfoodfacts.org/Logo_Annotation_Guidelines 
* https://annotate.openfoodfacts.org 
* Based on opencv/cvat: Powerful and efficient Computer Vision Annotation Tool (CVAT)  
* Currently 502 Bad Gateway: https://github.com/openfoodfacts/openfoodfacts-infrastructure/issues/49 
* Documentation: https://annotate.openfoodfacts.org/documentation/user_guide.html#creating-an-annotation-task 
* train a "universal" logo / label detector, with good results
* for each image crop resulting from the annotations (bounding box), generate embeddings with a pre-trained network (Resnet50). 
* This made it possible to verify that this approach is the right one for the classification of crops
* the results are in the presentation: 3 photos et c'est à peu près tout

#### Annotation guidelines
* there should be as little space as possible between the bounding box and the object. Conversely, the whole object must be included in the bounding box.
* if the object is partially hidden, indicate the object as "occluded" (click on the "profile" icon on the object in question, in the right panel)
* for best results, it is necessary that similar objects are annotated in the same way (especially concerning the extent of the object). It happens that there are several scales of annotation (cf the question discussed above of pictograms "to recycle"), the most important is that the annotations are coherent.
* several very similar images or concerning the same product follow one another in the dataset. For the next campaign, it will be better to shuffle the dataset to have as much diversity as possible (edited)


### Colab notebooks
* (Accessible by Pierre) https://colab.research.google.com/drive/1G-6OELcz8l1u1_53_0a2DAKRryIfB9CE 
* The predictions on the validation set: output_images
#### Pipeline on colab
* Data preprocessing : https://colab.research.google.com/drive/1cxi_aITHEFo4IZRsbiwm39CFgDKMG8LZ
* Model training : https://colab.research.google.com/drive/1qGz2tNC29IRqji4hKebmu249WaUP7u0_
* Visualization of results : https://colab.research.google.com/drive/1etqj-OgPEHi6ypjCixGSBTEW7muM6bc0

### Roadmap

### API routes
#### ANNResource: Allows you to do XYZ
/api/v1/ann/{logo_id:int}
#### ANNResource: Allows you to do XYZ
/api/v1/ann
#### ANNBatchResource: Allows you to do XYZ
/api/v1/ann/batch
#### ANNEmbeddingResource: Allows you to do XYZ
/api/v1/ann/from_embedding
#### AddLogoResource: Allows you to do XYZ
/api/v1/ann/add
#### ANNCountResource: Allows you to do XYZ
/api/v1/ann/count
#### ANNStoredLogoResource: Allows you to do XYZ
/api/v1/ann/stored

### Datasets

* https://openfoodfacts.slack.com/files/UN6TMCYA2/FNGUPS00H/off_barcode.csv 
* Photo archive: Archive.zip (995mo): https://drive.google.com/file/d/1-N79A9jpVzR-al8aNFJNWvs59wM_M6sx/view
* https://openfoodfacts.slack.com/files/UN6TMCYA2/FQWLFNPF0/relabeled_labels_brands.tfrecord 
* https://openfoodfacts.slack.com/files/UN6TMCYA2/FQWA1AZ9V/labels_brands.tfrecord 
* https://openfoodfacts.slack.com/files/UN6TMCYA2/FQFLJKYG2/relabel_tfrecord.ipynb 
