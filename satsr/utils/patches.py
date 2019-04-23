from __future__ import division
from random import randrange
import os
from math import ceil

import numpy as np
from skimage.transform import resize
import skimage.measure
from scipy.ndimage.filters import gaussian_filter


max_pixel = 2**16  # maximum possible pixel value
norm = 2000  # divide the pixel value to have a more normalized distribution


def interp_patches(lr_image, hr_image_shape):
    interp = np.zeros((lr_image.shape[0:2] + hr_image_shape[2:4])).astype(np.float32)
    for k in range(lr_image.shape[0]):
        for w in range(lr_image.shape[1]):
            interp[k, w] = resize(image=lr_image[k, w] / max_pixel,
                                  output_shape=hr_image_shape[2:4],
                                  mode='reflect') * max_pixel  # bilinear
    return interp


def upsample_patches(lr_patch, output_shape):
    """
    Make the bilinear upsampling before feeding the network
    lr_patch: shape(bands, H, W)
    """
    up_patches = np.zeros((lr_patch.shape[0], *output_shape)).astype(np.float32)
    for k in range(lr_patch.shape[0]):
        up_patches[k] = resize(image=lr_patch[k] / max_pixel,
                               output_shape=output_shape,
                               mode='reflect') * max_pixel
    return up_patches


def downPixelAggr(img, SCALE=2):
    """
    Downsample image
    """
    if len(img.shape) == 2:
        img = np.expand_dims(img, axis=-1)
    img_blur = np.zeros(img.shape)
    # Filter the image with a Gaussian filter
    for i in range(0, img.shape[2]):
        img_blur[:, :, i] = gaussian_filter(img[:, :, i], 1/SCALE)
    # New image dims
    new_dims = tuple(s//SCALE for s in img.shape)
    img_lr = np.zeros(new_dims[0:2]+(img.shape[-1],))
    # Iterate through all the image channels with avg pooling (pixel aggregation)
    for i in range(0, img.shape[2]):
        img_lr[:, :, i] = skimage.measure.block_reduce(img_blur[:, :, i], (SCALE, SCALE), np.mean)

    return img_lr


def get_test_patches(data_bands, patch_size=128, border=4, interp=True):
    # For 20: patchSize=128, border=8
    # For 60: patchSize=192, border=12

    resolutions = data_bands.keys()
    max_res, min_res = max(resolutions), min(resolutions)
    scales = {res: int(res/min_res) for res in resolutions}  # scale with respect to minimum resolution  e.g. {10: 1, 20: 2, 60: 6}
    inv_scales = {res: int(max_res/res) for res in resolutions}  # scale with respect to maximum resolution e.g. {10: 6, 20: 3, 60: 1} or {10: 2, 20: 1}

    # Normalize pixel values
    for res in resolutions:
        data_bands[res] = data_bands[res] / norm

    # Adapt the borders and patchsizes for each scale
    patch_size = int(patch_size/scales[max_res]) * scales[max_res]  # make patchsize compatible with all scales
    borders = {res: border//scales[res] for res in resolutions}
    patch_sizes = {res: (patch_size//scales[res], patch_size//scales[res]) for res in resolutions}

    # Mirror the data at the borders to have the same dimensions as the input
    padded_bands = {}
    for res in resolutions:
        tmp_border = border // scales[res]
        padded_bands[res] = np.pad(data_bands[res], ((tmp_border, tmp_border), (tmp_border, tmp_border), (0, 0)), mode='symmetric')

    # Compute the number of patches
    P_i = padded_bands[max_res].shape[0] - 2 * borders[max_res]
    P_j = padded_bands[max_res].shape[1] - 2 * borders[max_res]
    Q_i = patch_sizes[max_res][0] - 2 * borders[max_res]
    Q_j = patch_sizes[max_res][1] - 2 * borders[max_res]

    patchesAlongi = P_i // Q_i
    patchesAlongj = P_j // Q_j
    nr_patches = (patchesAlongi + 1) * (patchesAlongj + 1)

    range_i = np.arange(0, patchesAlongi) * Q_i
    range_j = np.arange(0, patchesAlongj) * Q_j
    if not np.mod(P_i, Q_i) == 0:
        range_i = np.append(range_i, padded_bands[max_res].shape[0] - patch_sizes[max_res][0])
    if not np.mod(P_j, Q_j) == 0:
        range_j = np.append(range_j, padded_bands[max_res].shape[1] - patch_sizes[max_res][0])

    # Save the patches
    images = {res: np.zeros((nr_patches, padded_bands[res].shape[2]) + patch_sizes[res]).astype(np.float32) for res in resolutions}
    pCount = 0
    for ii in range_i.astype(int):
        for jj in range_j.astype(int):
            upper_left_i = ii
            upper_left_j = jj
            crop_point = [upper_left_i,
                          upper_left_j,
                          upper_left_i + patch_sizes[max_res][0],
                          upper_left_j + patch_sizes[max_res][1]]
            for res in resolutions:
                tmp_crop_point = [p*inv_scales[res] for p in crop_point]
                tmp_cr_image = padded_bands[res][tmp_crop_point[0]:tmp_crop_point[2], tmp_crop_point[1]:tmp_crop_point[3]]
                images[res][pCount] = np.moveaxis(tmp_cr_image, source=2, destination=0)  # move to channels first
            pCount += 1

    if interp:
        for res in resolutions:
            images[res] = interp_patches(images[res], images[min_res].shape)

    return images


def save_random_patches(gt, lr, save_path, num_patches=None):
    """

    Parameters
    ----------
    gt : numpy array
        Array with the ground truth data of the maximal resolution
    lr : dict
    save_path : str
    num_patches : int
        Number of patches to take from the image. If None the number will be proportional to the image size.
    """
    resolutions = lr.keys()
    max_res, min_res = max(resolutions), min(resolutions)
    scales = {res: int(res/min_res) for res in resolutions}  # scale with respect to minimum resolution  e.g. {10: 1, 20: 2, 60: 6}
    inv_scales = {res: int(max_res/res) for res in resolutions}  # scale with respect to maximum resolution e.g. {10: 6, 20: 3, 60: 1} or {10: 2, 20: 1}

    PATCH_SIZE_LR = (16, 16)

    if num_patches is None:
        alpha = 5  # multiplier to scale number of patches wrt the size of the image
        num_patches = alpha * gt[:, :, 0].size / 16**2

    # Normalize pixel values
    gt = gt / norm
    for res in resolutions:
        lr[res] = lr[res] / norm

    for i, crop in enumerate(range(0, num_patches)):

        found = False
        count = 0
        while not found:
            # Sample a random crop point
            upper_left_x = randrange(0, lr[max_res].shape[0] - PATCH_SIZE_LR[0])
            upper_left_y = randrange(0, lr[max_res].shape[1] - PATCH_SIZE_LR[1])
            crop_point_lr = [upper_left_x,
                             upper_left_y,
                             upper_left_x + PATCH_SIZE_LR[0],
                             upper_left_y + PATCH_SIZE_LR[1]]

            # Create patches for HR map (label)
            mult_factor = scales[max_res]
            crop_point = [p * mult_factor for p in crop_point_lr]
            tmp_label = gt[crop_point[0]:crop_point[2], crop_point[1]:crop_point[3]]
            tmp_label = np.moveaxis(tmp_label, source=2, destination=0)  # move to channels first

            # If at least half of the crop has values different from 0 we keep the crop
            if (np.sum(tmp_label != 0) / tmp_label.size) > 0.5:
                found = True

            count += 1
            if count == 100:
                print('Error while taking patches from the image: it looks like the image is mostly made of zeros. '
                      'Skipping the tile ...')
                return None

        # Create patches for LR maps
        tmp_images = {}
        for res in lr.keys():
            mult_factor = inv_scales[res]
            crop_point = [p * mult_factor for p in crop_point_lr]
            tmp_images[res] = lr[res][crop_point[0]:crop_point[2], crop_point[1]:crop_point[3]]
            tmp_images[res] = np.moveaxis(tmp_images[res], source=2, destination=0)  # move to channels first

        # Make the bilinear upsampling
        for res in lr.keys():
            tmp_images[res] = upsample_patches(tmp_images[res], output_shape=tmp_images[min_res].shape[1:])

        # Save patches to numpy binaries
        for res in lr.keys():
            np.save(os.path.join(save_path, 'input{}_{}'.format(res, i)),
                    tmp_images[res])

        np.save(os.path.join(save_path, 'label{}_{}'.format(max_res, i)),
                tmp_label)


def recompose_images(a, border, size=None):
    """
    Recompose an image from the patches
    """
    if a.shape[0] == 1:
        images = a[0]
    else:
        # This is done because we do not mirror the data at the image border
        patch_size = a.shape[2] - border*2
        x_tiles = int(ceil(size[1]/float(patch_size)))
        y_tiles = int(ceil(size[0]/float(patch_size)))

        # Initialize image
        images = np.zeros((a.shape[1], size[0], size[1])).astype(np.float32)
        current_patch = 0
        for y in range(0, y_tiles):
            ypoint = y * patch_size
            if ypoint > size[0] - patch_size:
                ypoint = size[0] - patch_size
            for x in range(0, x_tiles):
                xpoint = x * patch_size
                if xpoint > size[1] - patch_size:
                    xpoint = size[1] - patch_size
                images[:, ypoint:ypoint+patch_size, xpoint:xpoint+patch_size] = a[current_patch, :, border:a.shape[2]-border, border:a.shape[3]-border]
                current_patch += 1

    # Undo the pixel values normalization
    images = images * norm

    # Clip the image to allowed pixel values
    images = np.clip(images, a_min=0, a_max=max_pixel)

    return images.transpose((1, 2, 0))
