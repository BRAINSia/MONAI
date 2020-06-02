# Copyright 2020 MONAI Consortium
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import os
import csv
import numpy as np
import torch
from collections import OrderedDict
from typing import Union, Optional


class CSVSaver:
    """
    save the data in a dictionary format cache, and write to a CSV file finally.
    Typically, the data can be classification predictions, call `save` for single data
    or call `save_batch` to save a batch of data together, and call `finalize` to write
    the cached data into CSV file. If no meta data provided, use index from 0 to save data.
    """

    def __init__(self, output_dir: str = "./", filename: str = "predictions.csv", overwrite: bool = True):
        """
        Args:
            output_dir: output CSV file directory.
            filename: name of the saved CSV file name.
            overwrite: whether to overwriting existing CSV file content. If we are not overwriting,
                then we check if the results have been previously saved, and load them to the prediction_dict.

        """
        self.output_dir: str = output_dir
        self._cache_dict: OrderedDict = OrderedDict()
        assert isinstance(filename, str) and filename[-4:] == ".csv", "filename must be a string with CSV format."
        self._filepath: str = os.path.join(output_dir, filename)
        self.overwrite: bool = overwrite
        self._data_index: int = 0

    def finalize(self) -> None:
        """
        Writes the cached dict to a csv

        """
        if not self.overwrite and os.path.exists(self._filepath):
            with open(self._filepath, "r") as f:
                reader = csv.reader(f)
                for row in reader:
                    self._cache_dict[row[0]] = np.array(row[1:]).astype(np.float32)

        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
        with open(self._filepath, "w") as f:
            for k, v in self._cache_dict.items():
                f.write(k)
                for result in v.flatten():
                    f.write("," + str(result))
                f.write("\n")

    def save(self, data: Union[torch.Tensor, np.ndarray], meta_data: Optional[dict] = None) -> None:
        """Save data into the cache dictionary. The metadata should have the following key:
            - ``'filename_or_obj'`` -- save the data corresponding to file name or object.
        If meta_data is None, use the default index from 0 to save data instead.

        args:
            data: target data content that save into cache.
            meta_data: the meta data information corresponding to the data.

        """
        save_key = meta_data["filename_or_obj"] if meta_data else str(self._data_index)
        self._data_index += 1
        out_data: np.ndarray = data.detach().cpu().numpy() if torch.is_tensor(data) else data
        self._cache_dict[save_key] = out_data.astype(np.float32)

    def save_batch(self, batch_data: Union[torch.Tensor, np.ndarray], meta_data: Optional[dict] = None) -> None:
        """Save a batch of data into the cache dictionary.

        args:
            batch_data: target batch data content that save into cache.
            meta_data: every key-value in the meta_data is corresponding to 1 batch of data.

        """
        for i, data in enumerate(batch_data):  # save a batch of files
            self.save(data, {k: meta_data[k][i] for k in meta_data} if meta_data else None)
