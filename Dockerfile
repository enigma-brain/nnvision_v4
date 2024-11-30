FROM sinzlab/pytorch:v3.8-torch1.7.0-cuda11.0-dj0.12.7
ENV DEBIAN_FRONTEND=noninteractive

# Install JupyterLab
RUN python3 -m pip install --upgrade pip
RUN python3 -m pip install jupyterlab
RUN pip3 install numpy==1.22.0
RUN pip3 install torch torchvision torchaudio
RUN pip3 install git+https://github.com/KonstantinWilleke/experanto.git@statshack
RUN pip3 install datajoint
RUN pip3 install opencv-python==4.8.0.74
RUN pip3 install mlflow
RUN pip3 install -U pytorch_warmup
RUN pip3 install transformers==4.28.0

#RUN pip3 install -e /notebooks/mousehiera

#ADD . /src/mousehiera
#RUN pip3 install -e /src/mousehiera

ADD . /notebooks
RUN pip3 install -e /notebooks

EXPOSE 8888
# By default start running jupyter notebook
WORKDIR /notebooks

#RUN git clone -b statshack https://github.com/KonstantinWilleke/experanto.git
#RUN pip3 install -e /src/experanto
ENTRYPOINT ["jupyter", "lab", "--allow-root", "--ip=0.0.0.0", "--no-browser", "--port=8888", "--NotebookApp.token='1234'", "--notebook-dir='/notebooks'"]
