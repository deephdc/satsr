from __future__ import division

from keras.models import Model, Input
from keras.layers import Conv2D, Concatenate, Activation, Lambda, Add
from keras import backend as K


K.set_image_data_format('channels_first')


def resBlock(x, channels, kernel_size=[3, 3], scale=0.1):
    tmp = Conv2D(channels, kernel_size, kernel_initializer='he_uniform', padding='same')(x)
    tmp = Activation('relu')(tmp)
    tmp = Conv2D(channels, kernel_size, kernel_initializer='he_uniform', padding='same')(tmp)
    tmp = Lambda(lambda x: x * scale)(tmp)

    return Add()([x, tmp])


def s2model(input_shapes, num_layers=32, feature_size=256):
    """
    Parameters
    ----------
    input_shapes : dict
    num_layers : int
    feature_size : int

    Returns
    -------
    Keras model

    Notes
    -----
    Original paper by Laharas et al also had a deep version with (num_layers=32, feature_size=256) although we disable
    default as the performance gains were minor in comparison with the shallow one.
    """

    input_list = []
    for res, shape in input_shapes.items(): # .items sorts by key values (unlike .iteritems)
        input_list.append(Input(shape=shape, name=res))

    x = Concatenate(axis=1)(input_list)
    x = Conv2D(feature_size, (3, 3), kernel_initializer='he_uniform', activation='relu', padding='same')(x)

    for i in range(num_layers):
        x = resBlock(x, feature_size)

    x = Conv2D(int(input_list[-1].shape[1]), (3, 3), kernel_initializer='he_uniform', padding='same')(x)
    # x = Dropout(0.3)(x)
    x = Add()([x, input_list[-1]]) # add input of the maximum resolution
    model = Model(inputs=input_list, outputs=x)
    return model
