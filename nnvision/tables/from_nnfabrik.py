import datajoint as dj

from copy import deepcopy

from nnfabrik.templates import TrainedModelBase, DataInfoBase
from nnfabrik.main import Model, Dataset, Trainer, Seed, Fabrikant
from nnfabrik.utility.dj_helpers import gitlog, make_hash
from nnfabrik.builder import resolve_data
from nnfabrik.utility.dj_helpers import CustomSchema

import os
from pathlib import Path
import pickle
from ..utility.dj_helpers import get_default_args
from .templates import (
    ScoringBase,
    MeasuresBase,
    SummaryMeasuresBase,
    SummaryScoringBase,
)


schema = CustomSchema(dj.config.get("nnfabrik.schema_name", "nnfabrik_core"))

if not "stores" in dj.config:
    dj.config["stores"] = {}
dj.config["stores"]["minio"] = {  # store in s3
    "protocol": "s3",
    "endpoint": os.environ.get("MINIO_ENDPOINT", "DUMMY_ENDPOINT"),
    "bucket": "nnfabrik",
    "location": "dj-store",
    "access_key": os.environ.get("MINIO_ACCESS_KEY", "FAKEKEY"),
    "secret_key": os.environ.get("MINIO_SECRET_KEY", "FAKEKEY"),
    "secure": True,
}


@schema
class DataInfo(DataInfoBase):

    dataset_table = Dataset
    user_table = Fabrikant

    def create_stats_files(self, key=None, path=None):

        if key == None:
            key = self.fetch("KEY")

            for restr in key:
                dataset_config = (self.dataset_table & restr).fetch1("dataset_config")
                image_cache_path = dataset_config.get("image_cache_path", None)
                if image_cache_path is None:
                    raise ValueError(
                        "The argument image_cache_path has to be specified in the dataset_config in order "
                        "to create the DataInfo"
                    )

                image_cache_path = image_cache_path.split("individual")[0]
                default_args = get_default_args(
                    resolve_data((self.dataset_table & restr).fetch1("dataset_fn"))
                )
                default_args.update(dataset_config)
                stats_filename = make_hash(default_args)
                stats_path = os.path.join(
                    path if path is not None else image_cache_path,
                    "statistics/",
                    stats_filename,
                )

                if not os.path.exists(stats_path):
                    data_info = (self & restr).fetch1("data_info")

                    stats_path_base = str(Path(stats_path).parent)
                    if not os.path.exists(stats_path_base):
                        os.mkdir(stats_path_base)
                    with open(stats_path, "wb") as pkl:
                        pickle.dump(data_info, pkl)


@schema
class TrainedModel(TrainedModelBase):
    table_comment = "Trained models"
    data_info_table = DataInfo
    storage = "minio"

    model_table = Model
    dataset_table = Dataset
    trainer_table = Trainer
    seed_table = Seed
    user_table = Fabrikant


@schema
class TrainedHyperModel(TrainedModelBase):
    table_comment = "Trained model table for hyperparam searches"
    data_info_table = DataInfo
    storage = "minio"

    model_table = Model
    dataset_table = Dataset
    trainer_table = Trainer
    seed_table = Seed
    user_table = Fabrikant


@schema
class TrainedTransferModel(TrainedModelBase):
    table_comment = "Trained models"
    data_info_table = DataInfo
    storage = "minio"

    model_table = Model
    dataset_table = Dataset
    trainer_table = Trainer
    seed_table = Seed
    user_table = Fabrikant


@schema
class SharedReadoutTrainedModel(TrainedModelBase):
    table_comment = "Trained models"
    data_info_table = DataInfo
    storage = "minio"

    model_table = Model
    dataset_table = Dataset
    trainer_table = Trainer
    seed_table = Seed
    user_table = Fabrikant


class ScoringTable(ScoringBase):
    """
    Overwrites the nnfabriks scoring template, to make it handle mouse repeat-dataloaders.
    """

    dataloader_function_kwargs = {}

    def get_repeats_dataloaders(self, key=None, **kwargs):
        if key is None:
            key = self.fetch1("KEY")
        dataloaders = (
            self.dataset_table().get_dataloader(key=key)
            if self.data_cache is None
            else self.data_cache.load(key=key)
        )
        return dataloaders["test"]


class ScoringBaseNeuronType(ScoringBase):
    """
    A class that modifies the the scoring template from nnfabrik to reflect the changed primary attributes of the Units
    table.
    """

    dataloader_function_kwargs = {}

    def get_repeats_dataloaders(self, key=None, **kwargs):
        if key is None:
            key = self.fetch1("KEY")
        dataloaders = (
            self.trainedmodel_table.dataset_table().get_dataloader(key=key)
            if self.data_cache is None
            else self.data_cache.load(key=key)
        )
        return dataloaders["test"]

    def insert_unit_measures(self, key, unit_measures_dict):
        key = deepcopy(key)
        keys_for_inserting = []
        for data_key, unit_scores in unit_measures_dict.items():
            unit_ids, unit_indices, unit_types = (
                (self.unit_table & key) & dict(data_key=data_key)
            ).fetch("unit_id", "unit_index", "unit_type", order_by="unit_index")
            for unit_index, (unit_score, unit_id, unit_type) in enumerate(
                zip(unit_scores, unit_indices, unit_types)
            ):
                if "unit_id" in key:
                    key.pop("unit_id")
                if "data_key" in key:
                    key.pop("data_key")
                assert (
                    unit_index == unit_indices[unit_index]
                ), "mismatch between unit ID and unit index"
                key["unit_id"] = unit_id
                key["unit_type"] = unit_type
                key["unit_{}".format(self.measure_attribute)] = unit_score
                key["data_key"] = data_key
                keys_for_inserting.append(key.copy())
        self.Units.insert(keys_for_inserting, ignore_extra_fields=True)


class MeasuresBaseNeuronType(MeasuresBase):
    """
    A class that modifies the the scoring template from nnfabrik to reflect the changed primary attributes of the Units
    table.
    """

    dataloader_function_kwargs = {}

    def get_repeats_dataloaders(self, key=None, **kwargs):
        if key is None:
            key = self.fetch1("KEY")
        dataloaders = (
            self.dataset_table().get_dataloader(key=key)
            if self.data_cache is None
            else self.data_cache.load(key=key)
        )
        return dataloaders["test"]

    def insert_unit_measures(self, key, unit_measures_dict):
        key = deepcopy(key)
        keys_for_inserting = []
        for data_key, unit_scores in unit_measures_dict.items():
            unit_ids, unit_indices, unit_types = (
                (self.unit_table & key) & dict(data_key=data_key)
            ).fetch("unit_id", "unit_index", "unit_type", order_by="unit_index")
            for unit_index, (unit_score, unit_id, unit_type) in enumerate(
                zip(unit_scores, unit_indices, unit_types)
            ):
                if "unit_id" in key:
                    key.pop("unit_id")
                if "data_key" in key:
                    key.pop("data_key")
                assert (
                    unit_index == unit_indices[unit_index]
                ), "mismatch between unit ID and unit index"
                key["unit_id"] = unit_id
                key["unit_type"] = unit_type
                key["unit_{}".format(self.measure_attribute)] = unit_score
                key["data_key"] = data_key
                keys_for_inserting.append(key.copy())
        self.Units.insert(keys_for_inserting, ignore_extra_fields=True)
