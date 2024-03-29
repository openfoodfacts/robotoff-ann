import pathlib
import random
from typing import Any, Dict, List, Optional

import annoy
import falcon
import numpy as np
from falcon.media.validators import jsonschema
from falcon_cors import CORS
from falcon_multipart.middleware import MultipartMiddleware
from sentry_sdk.integrations.falcon import FalconIntegration

import schema
import settings
from embeddings import EMBEDDING_STORE, add_logos
from utils import get_image_from_url, get_logger, text_file_iter

logger = get_logger()

settings.init_sentry(integrations=[FalconIntegration()])


class ANNIndex:
    """This class store an Annoy approximate nearest neighbors index and the
    keys associated with each item in the index. Each key corresponds to the
    logo annotation ID (primary key) in the LogoAnnotation table.
    
    :param index: An Annoy index
    :param keys: The ordered list of keys associated with the items in the
    index
    """

    def __init__(self, index: annoy.AnnoyIndex, keys: List[int]):
        self.index: annoy.AnnoyIndex = index
        self.keys: List[int] = keys
        self.key_to_ann_id = {x: i for i, x in enumerate(self.keys)}

    @classmethod
    def load(cls, index_dir: pathlib.Path) -> "ANNIndex":
        """Load an Annoy ANN index from an index directory.
        
        The directory must contain two files:
        - the index named index.bin
        - the external keys (logo annotation IDs) in a file named index.txt

        :param index_dir: The index directory to use
        """
        dimension = settings.INDEX_DIM[index_dir.name]
        index = annoy.AnnoyIndex(dimension, "euclidean")
        index.load(str(index_dir / settings.INDEX_FILE_NAME), prefault=True)
        keys = [int(x) for x in text_file_iter(index_dir / settings.KEYS_FILE_NAME)]
        return cls(index, keys)


logger.info("Loading ANN indexes...")
INDEXES: Dict[str, ANNIndex] = {
    index_dir.name: ANNIndex.load(index_dir)
    for index_dir in settings.DATA_DIR.iterdir()
    if index_dir.is_dir()
}
logger.info(f"Indexes loaded: {INDEXES.keys()}")


class ANNResource:
    def on_get(
        self, req: falcon.Request, resp: falcon.Response, logo_id: Optional[int] = None
    ):
        """Search for nearest neighbors of:
        - a random logo (if logo_id not provided)
        - a specific logo otherwise
        """
        index_name = req.get_param("index", default=settings.DEFAULT_INDEX)
        count = req.get_param_as_int("count", min_value=1, max_value=500, default=100)

        if index_name not in INDEXES:
            raise falcon.HTTPBadRequest("unknown index: {}".format(index_name))

        ann_index = INDEXES[index_name]

        if logo_id is None:
            logo_id = ann_index.keys[random.randint(0, len(ann_index.keys) - 1)]

        results = get_nearest_neighbors(ann_index, count, logo_id)

        if results is None:
            resp.status = falcon.HTTP_404
        else:
            resp.media = {"results": results, "count": len(results)}


class ANNBatchResource:
    def on_get(self, req: falcon.Request, resp: falcon.Response):
        """Batch version (several logos) of ANNResource."""
        index_name = req.get_param("index", default=settings.DEFAULT_INDEX)
        count = req.get_param_as_int("count", min_value=1, max_value=500, default=100)
        logo_ids = req.get_param_as_list(
            "logo_ids", required=True, transform=int, default=[]
        )
        logger.info(f"Received request for {index_name}, logos: {logo_ids}")

        if index_name not in INDEXES:
            raise falcon.HTTPBadRequest("unknown index: {}".format(index_name))

        ann_index = INDEXES[index_name]
        results = {}

        for logo_id in logo_ids:
            logo_results = get_nearest_neighbors(ann_index, count, logo_id)

            if logo_results is not None:
                results[logo_id] = logo_results

        resp.media = {
            "results": results,
            "count": len(results),
        }


def get_nearest_neighbors(
    ann_index: ANNIndex, count: int, logo_id: int
) -> Optional[List[Dict[str, Any]]]:
    """Return the nearest neighbors of a logo, using the ANN index.
    
    The way we find nearest neighbors depends on whether the queried logo is
    indexed in the ANN:
    - if it is, we simply get the item index in the ANN index and query nearest
    neighbors using get_nns_by_item
    - otherwise we fetch the logo embedding in the EmbeddingStore and query
    nearest neighbors using get_nns_by_vector.
    This EmbeddingStore is updated with new logo embeddings each time POST /ann/add
    is called from robotoff.

    :param ann_index: The ANN index to use
    :param count: The number of results to return
    :param logo_id: The logo external ID (primary key in LogoAnnotation table)
    to use as query
    """
    if logo_id in ann_index.key_to_ann_id:
        logger.info(f"Trying to get nns for logo `{logo_id}`")
        item_index = ann_index.key_to_ann_id[logo_id]
        indexes, distances = ann_index.index.get_nns_by_item(
            item_index, count, include_distances=True
        )
        logger.info("Successfully retrieved distances and indexes")
    else:
        logger.info(f"Trying to get an embedding for logo `{logo_id}`")
        embedding = EMBEDDING_STORE.get_embedding(logo_id)
        logger.info(f"Found an embedding: {embedding}")
        if embedding is None:
            return None

        indexes, distances = ann_index.index.get_nns_by_vector(
            embedding, count, include_distances=True
        )
        logger.info("Successfully retrieved distances and indexes")

    logo_ids = [ann_index.keys[index] for index in indexes]
    results = []

    for ann_logo_id, distance in zip(logo_ids, distances):
        results.append({"distance": distance, "logo_id": ann_logo_id})

    return results


class ANNEmbeddingResource:
    def on_post(self, req: falcon.Request, resp: falcon.Response):
        """Search for nearest neighbors using an embedding as input.
        
        Note that it's the client responsability to make sure the embedding
        has been generated using the same model as the one that generated index
        embeddings.
        """
        index_name = req.get_param("index", default=settings.DEFAULT_INDEX)

        if index_name not in INDEXES:
            raise falcon.HTTPBadRequest("unknown index: {}".format(index_name))

        ann_index = INDEXES[index_name]

        count = req.media.get("count", 1)
        embedding = req.media["embedding"]

        if len(embedding) != settings.INDEX_DIM:
            raise falcon.HTTPBadRequest(
                "invalid dimension",
                "embedding must be of size {}, here: {}".format(
                    settings.INDEX_DIM, len(embedding)
                ),
            )

        indexes, distances = ann_index.index.get_nns_by_vector(
            embedding, count, include_distances=True
        )

        logo_ids = [ann_index.keys[index] for index in indexes]
        results = []

        for ann_logo_id, distance in zip(logo_ids, distances):
            results.append({"distance": distance, "logo_id": ann_logo_id})

        resp.media = {"results": results, "count": len(results)}


class AddLogoResource:
    @jsonschema.validate(schema.ADD_LOGO_SCHEMA)
    def on_post(self, req: falcon.Request, resp: falcon.Response):
        """Compute the embeddings of newly detected logos and store them in
        the EmbeddingStore.

        This allow nearest neighbors to be computed on new logos.
        """
        image_url = req.media["image_url"]
        logos = req.media["logos"]
        logo_ids = [logo["id"] for logo in logos]

        if all(logo_id in EMBEDDING_STORE for logo_id in logo_ids):
            resp.media = {
                "added": 0,
            }
            return

        bounding_boxes = [logo["bounding_box"] for logo in logos]

        image = get_image_from_url(image_url)

        if image is None:
            raise falcon.HTTPBadRequest("invalid image")

        if np.array(image).shape[-1] != 3:
            image = image.convert("RGB")

        added = add_logos(image, logo_ids, bounding_boxes)
        resp.media = {
            "added": added,
        }


class ANNCountResource:
    def on_get(self, req: falcon.Request, resp: falcon.Response):
        """Return the number of logos stored in the EmbeddingStore (number of
        logos that can be used as query)."""
        resp.media = {"count": len(EMBEDDING_STORE)}


class ANNStoredLogoResource:
    def on_get(self, req: falcon.Request, resp: falcon.Response):
        """Return the list of logo IDs stored in the EmbeddingStore."""
        resp.media = {"stored": list(EMBEDDING_STORE.get_logo_ids())}


cors = CORS(
    allow_all_origins=True,
    allow_all_headers=True,
    allow_all_methods=True,
    allow_credentials_all_origins=True,
    max_age=600,
)

api = falcon.API(middleware=[cors.middleware, MultipartMiddleware()])

# Parse form parameters
api.req_options.auto_parse_form_urlencoded = True
api.req_options.strip_url_path_trailing_slash = True
api.req_options.auto_parse_qs_csv = True
api.add_route("/api/v1/ann/{logo_id:int}", ANNResource())
api.add_route("/api/v1/ann", ANNResource())
api.add_route("/api/v1/ann/batch", ANNBatchResource())
api.add_route("/api/v1/ann/from_embedding", ANNEmbeddingResource())
api.add_route("/api/v1/ann/add", AddLogoResource())
api.add_route("/api/v1/ann/count", ANNCountResource())
api.add_route("/api/v1/ann/stored", ANNStoredLogoResource())
