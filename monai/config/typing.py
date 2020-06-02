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

# This file contains type information that should be used consistently throughout
# the entire MONAI package.
from enum import IntEnum
from typing import Hashable, Iterable, Sequence, TypeVar, Union

# The MonaiDictionaryKeySelection type is used to for defining variables
# that store a subset of keys to select items from a dictionary.
# The keys must be hashable, and if a container of keys is specified, the
# container must be iterable.
MonaiDictionaryKeySelection = TypeVar("MonaiDictionaryKeySelection", Iterable[Hashable], Hashable)


# The MonaiIndexSelection type is used to for defining variables
# that store a subset of indexes to select items from a List or Array like objects.
# The indexes must be integers, and if a container of indexes is specified, the
# container must be iterable.
MonaiIndexSelection = TypeVar("MonaiIndexSelection", Iterable[int], int)


class InterpolationOrder(IntEnum):
    """
    A convenience enumeration for the order of a spline interpolation.
    """

    SPLINE0 = 0
    NEARESTNEIGHBOR = 0
    SPLINE1 = 1
    LINEAR = 1
    SPLINE2 = 2
    CUBIC = 2
    SPLINE3 = 3
    SPLINE4 = 4
    SPLINE5 = 5


InterpolationOrderType = Union[int, InterpolationOrder]
InterpolationOrderSequenceType = Union[InterpolationOrder, Sequence[InterpolationOrder]]
