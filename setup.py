#!/usr/bin/env python
from setuptools import setup, find_packages
from os import path

here = path.abspath(path.dirname(__file__))

setup(
    name="nnvision",
    version="0.1",
    description="Envisioning the biological visual system with DNN",
    author="Konstantin Willeke",
    author_email="konstantin.willeke@gmail.com",
    packages=find_packages(exclude=[]),
    package_dir={"nnvision": "nnvision"},
    install_requires=[
        "setuptools>=50.3.2",
        "einops",
        "scikit-image==0.19.1",
        "numpy>=1.22.0",
        "matplotlib>=3.3.2",
        "scipy>=1.5.4",
        "torch>=1.7.0",
        "torchvision>=0.8.1",
        "GitPython>=3.1.30",
        "transformers>=4.35.2",
        "tqdm>=4.51.0",
        "nnfabrik @ git+https://github.com/sinzlab/nnfabrik.git@0.2.2",
        "neuralpredictors @ git+https://github.com/KonstantinWilleke/neuralpredictors.git@interview",
        "mei @ git+https://github.com/sinzlab/mei.git@inception_loop",
        "ptrnets @ git+https://github.com/sacadena/ptrnets.git@6f459a130ff2fb1a73f29d933e6bea5b435341e7"],
    package_data={
        "nnvison": [
            "data/model_weights/*.pth.tar",
            "data/model_weights/*.pth",
            "data/model_weights/*.tar",
            "data/model_weights/v4_multihead_attention_SOTA.pth.tar",
        ],
    },
)
