import os
import shutil

import numpy as np
from keras.utils import Sequence

from satsr import paths, main_sat
from satsr.utils.patches import downPixelAggr, save_random_patches


def load_data_splits(splits_dir, split_name='train'):
    """
    Load the data arrays from the [train/val/test].txt files.

    Parameters
    ----------
    im_dir : str
        Absolute path to the image folder.
    split_name : str
        Name of the data split to load
    Returns
    -------
    X : Numpy array of strs
        First colunm: Contains 'absolute_path_to_file' to images.
    """
    if '{}.txt'.format(split_name) not in os.listdir(splits_dir):
        raise ValueError("Invalid value for the split_name parameter: there is no `{}.txt` file in the `{}` "
                         "directory.".format(split_name, splits_dir))

    # Loading splits
    print("Loading {} data...".format(split_name))
    split = np.genfromtxt(os.path.join(splits_dir, '{}.txt'.format(split_name)), dtype='str', delimiter=' ')

    return split


def create_patches(tiles, max_res, tiles_dir=None, save_dir=None, roi_x_y=None, num_patches=None):
    """

    Parameters
    ----------
    tiles : list
    max_res : int
    roi_x_y : list
    tiles_dir : str
    save_dir : str
    num_patches : int

    Returns
    -------
    """
    if isinstance(tiles, str):
        tiles = [tiles]

    for tile in tiles:
        print('Creating patches for {} ...'.format(tile))
        tile_path = os.path.join(tiles_dir, tile)

        # Clearing previous patches (if any)
        output_dir = os.path.join(save_dir, os.path.basename(tile_path))
        if os.path.isdir(output_dir):
            shutil.rmtree(output_dir)
        os.mkdir(output_dir)

        data_bands, coord = main_sat.read_bands()(tile_path=tile_path, roi_x_y=roi_x_y, max_res=max_res)

        resolutions = data_bands.keys()
        max_res, min_res = max(resolutions), min(resolutions)
        scales = {res: int(res / min_res) for res in resolutions}  # scale with respect to minimum resolution  e.g. {10: 1, 20: 2, 60: 6}
        inv_scales = {res: int(max_res / res) for res in resolutions}  # scale with respect to maximum resolution e.g. {10: 6, 20: 3, 60: 1} or {10: 2, 20: 1}
        scale = scales[max_res]

        chan3 = data_bands[min_res][:, :, 0]
        vis = (chan3 < 1).astype(np.int)
        if np.sum(vis) > 0:
            print('The selected image has some blank pixels')
            # sys.exit()

        # Crop GT maps so that they can be correctly downscaled
        old_H, old_W = data_bands[max_res].shape[:2]  # size of the smallest map
        new_H, new_W = np.int(old_H/scale) * scale, np.int(old_W/scale) * scale
        for res, bands in data_bands.items():
            tmp_H, tmp_W = inv_scales[res] * new_H, inv_scales[res] * new_W
            data_bands[res] = bands[:tmp_H, :tmp_W, :]

        # Create the LR maps
        gt = data_bands
        lr = {res: None for res in gt.keys()}
        for res, gt_maps in gt.items():
            lr[res] = downPixelAggr(gt_maps, SCALE=scale)

        save_random_patches(gt=gt[max_res], lr=lr, save_path=output_dir, num_patches=num_patches)


class data_sequence(Sequence):
    """
    Instance of a Keras Sequence that is safer to use with multiprocessing than a standard generator.
    Check https://stanford.edu/~shervine/blog/keras-how-to-generate-data-on-the-fly
    TODO: Add sample weights on request
    """

    def __init__(self, tiles, max_res, batch_size=32, patches_dir=paths.get_patches_dir(), scale=2000,
                 shuffle=True):
        """
        Parameters are the same as in the data_generator function

        Parameters
        ----------
        tiles : list of strs
        resolutions : list of ints
        batch_size : int
        patches_dir : str
        scale : int
        shuffle : bool
        """
        if isinstance(tiles, str):
            tiles = [tiles]

        resolutions = [res for res in main_sat.res_to_bands().keys() if res <= max_res]
        self.label_res = np.amax(resolutions)  # resolution of the labels
        inputs, labels = self.tiles_to_samples(tiles, patches_dir, resolutions)
        assert len(inputs) == len(labels)

        self.inputs = inputs
        self.labels = labels
        self.scale = scale
        self.resolutions = [str(res) for res in sorted(resolutions)]
        self.batch_size = np.amin((batch_size, len(inputs)))
        self.shuffle = shuffle
        self.on_epoch_end()

    def tiles_to_samples(self, tiles, patches_dir, resolutions):
        inputs, labels = [], []
        for tilename in tiles:
            tilepath = os.path.join(patches_dir, tilename)

            # Get num_patches
            file_list = os.listdir(tilepath)
            if not file_list:
                continue
            else:
                nums = [int(f.split('_')[1].split('.')[0]) for f in file_list]
                num_patches = np.amax(nums) + 1

            for i in range(num_patches):
                tmp_input = {str(res): os.path.join(tilepath, 'input{}_{}.npy'.format(res, i)) for res in resolutions}
                tmp_label = os.path.join(tilepath, 'label{}_{}.npy'.format(self.label_res, i))

                inputs.append(tmp_input)
                labels.append(tmp_label)

        return inputs, labels

    def __len__(self):
        return int(np.ceil(len(self.inputs) / float(self.batch_size)))

    def __getitem__(self, idx):
        batch_idxs = self.indexes[idx*self.batch_size: (idx+1)*self.batch_size]

        batch_X = {res: [] for res in self.resolutions}
        batch_y = []
        for i in batch_idxs:
            batch_y.append(np.load(self.labels[i]))
            for res in self.resolutions:
                batch_X[res].append(np.load(self.inputs[i][res]))

        for k, v in batch_X.items():
            batch_X[k] = np.array(v)

        return batch_X, np.array(batch_y)

    def on_epoch_end(self):
        """Updates indexes after each epoch"""
        self.indexes = np.arange(len(self.inputs))
        if self.shuffle:
            np.random.shuffle(self.indexes)
