import torch
import os

from ..ptrmodels import task_core_gauss_readout


model_fn = task_core_gauss_readout
model_config = {'input_channels': 3,
             'model_name': 'resnet50_l2_eps0_1',
             'layer_name': 'layer3.0',
             'pretrained': False,
             'bias': False,
             'final_batchnorm': True,
             'final_nonlinearity': True,
             'momentum': 0.1,
             'fine_tune': False,
             'init_mu_range': 0.4,
             'init_sigma_range': 0.6,
             'readout_bias': True,
             'gamma_readout': 3.0,
             'gauss_type': 'isotropic',
             'elu_offset': -1}

data_info = {
    "all_sessions": {
        "input_dimensions": torch.Size([64, 3, 100, 100]),
        "input_channels": 3, # RGB
        "output_dimension": 394, # number of neurons
        "img_mean": 113.5,
        "img_std": 59.58,
    }}

current_dir = os.path.dirname(__file__)
filename = os.path.join(
    current_dir,
    "../../data/model_weights/v4_task_driven/44370def81b37c0588e260d6284610fe.pth.tar",
)
state_dict = torch.load(filename)

# load single model
v4_task_driven_resnet_model = model_fn(
    seed=0,
    dataloaders=None,
    **model_config,
    data_info=data_info,
)
v4_task_driven_resnet_model.load_state_dict(state_dict)

# load ensemble model
from mei.modules import EnsembleModel

# fill the list ensemble names with task driven 01 - 10
ensemble_names = [
    "33bd3a8c2c7dd6916c98ba7ad557eade.pth.tar",
    "44370def81b37c0588e260d6284610fe.pth.tar",
    "a1e5fa8957a5e802b51d70c31c87b62b.pth.tar",
    "ad6a12061d8a8ba02d04dd7b142ebc71.pth.tar",
    "c0f9f75fd8743c363df3f32dfbf88a7f.pth.tar",
]

base_dir = os.path.dirname(filename)
ensemble_models = []

for f in ensemble_names:
    ensemble_filename = os.path.join(base_dir, f)
    ensemble_state_dict = torch.load(ensemble_filename)
    ensemble_model = model_fn(
        seed=0,
        dataloaders=None,
        **model_config,
        data_info=data_info,
    )
    ensemble_model.load_state_dict(ensemble_state_dict)
    ensemble_models.append(ensemble_model)

ensemble_model = EnsembleModel(*ensemble_models)
