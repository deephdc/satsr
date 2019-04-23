DEEP Open Catalogue: satsr
==========================

**Author/Mantainer:** [Ignacio Heredia](https://github.com/IgnacioHeredia) (CSIC)

**Project:** This work is part of the [DEEP Hybrid-DataCloud](https://deep-hybrid-datacloud.eu/) project that has received
funding from the European Union’s Horizon 2020 research and innovation programme under grant agreement No 777435.

This is a plug-and-play tool to perform super-resolution on satellite imagery. Some demo images of the super-resolutions can be found [here](./reports/figures). Right now we are supporting super-resolution for the following satellites:

* [Sentinel 2](https://sentinel.esa.int/web/sentinel/missions/sentinel-2) 
* [LandSat 8](https://landsat.gsfc.nasa.gov/landsat-8/)

If you want to perform super-resolution on another satellite, go to the [training section](#train-other-satellites) to see how you can easily add support for additional satellites. We are happy to accept PRs!

You can find more information about it in the [DEEP Marketplace](https://marketplace.deep-hybrid-datacloud.eu/).

![demo_superres](./reports/figures/demo.png)


## Installing this module

### Local installation

**Requirements**
 
- This project has been tested in Ubuntu 18.04 with Python 3.6.5. Further package requirements are described in the `requirements.txt` file.
- It is a requirement to have [Tensorflow>=1.12.0 installed](https://www.tensorflow.org/install/pip) (either in gpu or cpu mode). 
This is not listed in the `requirements.txt` as it [breaks GPU support](https://github.com/tensorflow/tensorflow/issues/7166).
- This package needs the `GDAL` library (version >2.4.1). You can either install it with `conda` (with `conda install gdal`) or install it
with `pip` after having installed some additional external libraries. You can install those libraries in Linux with:

    ```bash
    sudo add-apt-repository -y ppa:ubuntugis/ubuntugis-unstable
    sudo apt update
    sudo apt install -y gdal-bin python-gdal python3-gdal
    ```

To start using this framework run:

```bash
git clone https://github.com/deephdc/satsr
cd satsr
pip install -e .
```

To use this module with an API you have to install the [DEEPaaS](https://github.com/indigo-dc/DEEPaaS)
package (temporarily, until `1.0` launching, you will have to use the `test-args` branch):

```bash
git clone -b test-args https://github.com/indigo-dc/deepaas
cd deepaas
pip install -e .
```

and run `deepaas-run --listen-ip 0.0.0.0`. Now open http://0.0.0.0:5000/ and look for the methods belonging to the `satsr` module.

### Docker installation

We have also prepared a ready-to-use [Docker container](https://github.com/deephdc/DEEP-OC-satsr) to run this module. To run it:

```bash
docker search deephdc
docker run -ti -p 5000:5000 deephdc/deep-oc-satsr
```

Now open http://0.0.0.0:5000/ and look for the methods belonging to the `satsr` module.


## Train other satellites

If you have images from a satellite that is not currently supported  you can esaily add support for you satellite:

*  Go to `./satsr/satellites` and create a `mynewsat.py` file. This file should contains basic information like resolutions, bands names and functions for opening the bands. Check the `landsat8.py` for a model on what parameters and functions have to be defined.
* *Optional:* You can also create another file like  `mynewsat_download.py` to support downloading data directly with Python.
* Link you newly created files with the satellite names by modifying the file `./satsr/main_sat.py`.
* Download training data (you can use the file `data_download.py` for convenience).
* Create in `./data/dataset_files` a `train.txt` file with the tile names of the folders you want to train with. You can also create a `val.txt` if you want to use validation during training.
* Run the `TRAIN` method in the DEEPaaS API with your training configuration.
* Rename the output timestamped folder in `./models` to something like `mynewsat_model_*m`.

Now you proceed to the next section to use you newly trained model to perfom super-resolution. If you are happy with the performance of your model we accept PRs to add it to the catalogue!


## Perform superresolution

There are two possible ways to use the `PREDICT` method from the DEEPaaS API:

* supply to the `data` argument a path  pointing to a compressed file (`zip` or tarball) containing your satellite tile.
* supply to the `url` argument an online url  of a compressed file (`zip` or tarball) containing your satellite tile.
Here is an [example](https://cephrgw01.ifca.es:8080/swift/v1/demo-test-Sentinel2-tile/S2A_MSIL1C_20170608T105651_N0205_R094_T30TWM_20170608T110453.SAFE.zip) of such an url for the Sentinel-2 that you can use for testing purposes.


## Acknowledgments

The code in this project is based on the [original repo](https://github.com/lanha/DSen2) by [Charis Lanaras](https://github.com/lanha) of the paper
[Super-Resolution of Sentinel-2 Images: Learning a Globally Applicable Deep Neural Network](https://arxiv.org/abs/1803.04271).

The main changes with respect to the original repo are that:

* most of the code has been either rewritten, restructured or cleaned up for better modularity, in order to make it plug-and-playable with
  other satellites (like LandSat).
* the code has been packaged into an installable Python package.
* it has been made compatible with the [DEEPaaS API](http://docs.deep-hybrid-datacloud.eu/en/latest/user/overview/api.html).
* some minor bugs have been corrected (and contributed back into the original repo in [#5](https://github.com/lanha/DSen2/pull/5) and [#6](https://github.com/lanha/DSen2/issues/6)).

If you consider this project to be useful, please consider citing the [original paper](https://arxiv.org/abs/1803.04271):

```
@article{lanaras2018super,
  title={Super-Resolution of Sentinel-2 Images: Learning a Globally Applicable Deep Neural Network},
  author={Lanaras, Charis and Bioucas-Dias, Jos{\'e} and Galliani, Silvano and Baltsavias, Emmanuel and Schindler, Konrad},
  journal={arXiv preprint arXiv:1803.04271},
  year={2018}
}
```
