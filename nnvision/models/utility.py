import torch
import copy
import functools
import numpy as np


def rsetattr(obj, attr, val):
    pre, _, post = attr.rpartition(".")
    return setattr(rgetattr(obj, pre) if pre else obj, post, val)


# using wonder's beautiful simplification: https://stackoverflow.com/questions/31174295/getattr-and-setattr-on-nested-objects/31174427?noredirect=1#comment86638618_31174427


def rgetattr(obj, attr, *args):
    def _getattr(obj, attr):
        return getattr(obj, attr, *args)

    return functools.reduce(_getattr, [obj] + attr.split("."))


def unpack_data_info(data_info):

    in_shapes_dict = {k: v["input_dimensions"] for k, v in data_info.items()}
    input_channels = [v["input_channels"] for k, v in data_info.items()]
    n_neurons_dict = {k: v["output_dimension"] for k, v in data_info.items()}
    return n_neurons_dict, in_shapes_dict, input_channels


def purge_state_dict(state_dict, purge_key=None, survival_key=None):

    if (purge_key is None) and (survival_key is None):
        raise ValueError(
            "purge_key and survival_key can not both be None. At least one key has to be defined"
        )

    purged_state_dict = copy.deepcopy(state_dict)

    for dict_key in state_dict.keys():
        if (purge_key is not None) and (purge_key in dict_key):
            purged_state_dict.pop(dict_key)
        elif (survival_key is not None) and (survival_key not in dict_key):
            purged_state_dict.pop(dict_key)

    return purged_state_dict


def get_readout_key_names(model):
    data_key = list(model.readout.keys())[0]
    readout = model.readout[data_key]

    feature_name = "features"
    if "mu" in dir(readout):
        feature_name = "features"
        grid_name = "mu"
        bias_name = "bias"
    else:
        feature_name = "features"
        grid_name = "grid"
        bias_name = "bias"

    return feature_name, grid_name, bias_name


def clip_convnext_layers(model, layer_name):
    indices, names = [], []
    for n, (i, j) in enumerate(model.named_modules()):
        names.append(i)
        indices.append(n)
    names = np.array(names)
    cut_layer_index = np.where(names == layer_name)[0].item()

    for n in names[cut_layer_index:]:
        rsetattr(model, n, torch.nn.Identity())

    return model

# helper functions concerning the ANN architecture

import torch
from torch import nn

import numpy as np
import random


def get_io_dims(data_loader):
    """
    Returns the shape of the dataset for each item within an entry returned by the `data_loader`
    The DataLoader object must return either a namedtuple, dictionary or a plain tuple.
    If `data_loader` entry is a namedtuple or a dictionary, a dictionary with the same keys as the
    namedtuple/dict item is returned, where values are the shape of the entry. Otherwise, a tuple of
    shape information is returned.

    Note that the first dimension is always the batch dim with size depending on the data_loader configuration.

    Args:
        data_loader (torch.DataLoader): is expected to be a pytorch Dataloader object returning
            either a namedtuple, dictionary, or a plain tuple.
    Returns:
        dict or tuple: If data_loader element is either namedtuple or dictionary, a ditionary
            of shape information, keyed for each entry of dataset is returned. Otherwise, a tuple
            of shape information is returned. The first dimension is always the batch dim
            with size depending on the data_loader configuration.
    """
    items = next(iter(data_loader))
    if hasattr(items, "_asdict"):  # if it's a named tuple
        items = items._asdict()

    if hasattr(items, "items"):  # if dict like
        return {k: v.shape for k, v in items.items()}
    else:
        return (v.shape for v in items)


def get_dims_for_loader_dict(dataloaders):
    """
    Given a dictionary of DataLoaders, returns a dictionary with same keys as the
    input and shape information (as returned by `get_io_dims`) on each keyed DataLoader.

    Args:
        dataloaders (dict of DataLoader): Dictionary of dataloaders.

    Returns:
        dict: A dict containing the result of calling `get_io_dims` for each entry of the input dict
    """
    return {k: get_io_dims(v) for k, v in dataloaders.items()}


def set_random_seed(seed: int, deterministic: bool = True):
    """
    Set random generator seed for Python interpreter, NumPy and PyTorch. When setting the seed for PyTorch,
    if CUDA device is available, manual seed for CUDA will also be set. Finally, if `deterministic=True`,
    and CUDA device is available, PyTorch CUDNN backend will be configured to `benchmark=False` and `deterministic=True`
    to yield as deterministic result as possible. For more details, refer to
    PyTorch documentation on reproducibility: https://pytorch.org/docs/stable/notes/randomness.html

    Beware that the seed setting is a "best effort" towards deterministic run. However, as detailed in the above documentation,
    there are certain PyTorch CUDA opertaions that are inherently non-deterministic, and there is no simple way to control for them.
    Thus, it is best to assume that when CUDA is utilized, operation of the PyTorch module will not be deterministic and thus
    not completely reproducible.

    Args:
        seed (int): seed value to be set
        deterministic (bool, optional): If True, CUDNN backend (if available) is set to be deterministic. Defaults to True. Note that if set
            to False, the CUDNN properties remain untouched and it NOT explicitly set to False.
    """
    random.seed(seed)
    np.random.seed(seed)
    if deterministic:
        torch.backends.cudnn.benchmark = False
        torch.backends.cudnn.deterministic = True
    torch.manual_seed(seed)  # this sets both CPU and CUDA seeds for PyTorch


def move_to_device(model, gpu=True, multi_gpu=True):
    """
    Moves given model to GPU(s) if they are available
    :param model: (torch.nn.Module) model to move
    :param gpu: (bool) if True attempt to move to GPU
    :param multi_gpu: (bool) if True attempt to use multi-GPU
    :return: torch.nn.Module, str
    """
    device = "cuda" if torch.cuda.is_available() and gpu else "cpu"
    if multi_gpu and torch.cuda.device_count() > 1:
        print("Using ", torch.cuda.device_count(), "GPUs")
        model = nn.DataParallel(model)
    model = model.to(device)
    return model, device


def find_prefix(keys: list, p_agree: float = 0.66, separator=".") -> (list, int):
    """
    Finds common prefix among state_dict keys
    :param keys: list of strings to find a common prefix
    :param p_agree: percentage of keys that should agree for a valid prefix
    :param separator: string that separates keys into substrings, e.g. "model.conv1.bias"
    :return: (prefix, end index of prefix)
    """
    keys = [k.split(separator) for k in keys]
    p_len = 0
    common_prefix = ""
    prefs = {"": len(keys)}
    while True:
        sorted_prefs = sorted(prefs.items(), key=lambda x: x[1], reverse=True)
        # check if largest count is above threshold
        if sorted_prefs[0][1] < p_agree * len(keys):
            break
        common_prefix = sorted_prefs[0][0]  # save prefix

        p_len += 1
        prefs = {}
        for key in keys:
            if p_len == len(key):  # prefix cannot be an entire key
                continue
            p_str = ".".join(key[:p_len])
            prefs[p_str] = prefs.get(p_str, 0) + 1
    return common_prefix, p_len - 1


def load_state_dict(
    model,
    state_dict: dict,
    ignore_missing: bool = False,
    ignore_unused: bool = False,
    match_names: bool = False,
    ignore_dim_mismatch: bool = False,
    prefix_agreement: float = 0.66,
):
    """
    Loads given state_dict into model, but allows for some more flexible loading.

    :param model: nn.Module object
    :param state_dict: dictionary containing a whole state of the module (result of `some_model.state_dict()`)
    :param ignore_missing: if True ignores entries present in model but not in `state_dict`
    :param match_names: if True tries to match names in `state_dict` and `model.state_dict()`
                        by finding and removing a common prefix from the keys in each dict
    :param ignore_dim_mismatch: if True ignores parameters in `state_dict` that don't fit the shape in `model`
    """

    model_dict = model.state_dict()
    # 0. Try to match names by adding or removing prefix:
    if match_names:
        # find prefix keys of each state dict:
        s_pref, s_idx = find_prefix(list(state_dict.keys()), p_agree=prefix_agreement)
        m_pref, m_idx = find_prefix(list(model_dict.keys()), p_agree=prefix_agreement)
        # switch prefixes:
        stripped_state_dict = {}
        for k, v in state_dict.items():
            if k.split(".")[:s_idx] == s_pref.split("."):
                stripped_key = ".".join(k.split(".")[s_idx:])
            else:
                stripped_key = k
            new_key = m_pref + "." + stripped_key if m_pref else stripped_key
            stripped_state_dict[new_key] = v
        state_dict = stripped_state_dict

    # 1. filter out missing keys
    filtered_state_dict = {k: v for k, v in state_dict.items() if k in model_dict}
    unused = set(state_dict.keys()) - set(filtered_state_dict.keys())
    if unused and ignore_unused:
        print("Ignored unnecessary keys in pretrained dict:\n" + "\n".join(unused))
    elif unused:
        raise RuntimeError("Error in loading state_dict: Unused keys:\n" + "\n".join(unused))
    missing = set(model_dict.keys()) - set(filtered_state_dict.keys())
    if missing and ignore_missing:
        print("Ignored Missing keys:\n" + "\n".join(missing))
    elif missing:
        raise RuntimeError("Error in loading state_dict: Missing keys:\n" + "\n".join(missing))

    # 2. overwrite entries in the existing state dict
    updated_model_dict = {}
    for k, v in filtered_state_dict.items():
        if v.shape != model_dict[k].shape:
            if ignore_dim_mismatch:
                print("Ignored shape-mismatched parameter:", k)
                continue
            else:
                raise RuntimeError("Error in loading state_dict: Shape-mismatch for key {}".format(k))
        updated_model_dict[k] = v

    # 3. load the new state dict
    model.load_state_dict(updated_model_dict, strict=(not ignore_missing))

