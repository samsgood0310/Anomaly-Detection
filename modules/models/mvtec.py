import tensorflow as tf
from tensorflow import keras


def build_model(channels=3):
    """Model mentionned in the MVTec Paper, originally proposed by Bergmann et Al. 
    Implemented here with an additional convolutional layer at the beginning to 
    accomodate the larger input size of 256 x 256 instead of 128 x 128.    
    Note: Using using Keras's sequential API """
    conv_encoder = keras.models.Sequential(
        [
            # keras.layers.InputLayer(input_shape=(256, 256, channels)),
            keras.layers.Conv2D(
                32,
                kernel_size=4,
                strides=2,
                padding="SAME",
                activation=keras.layers.LeakyReLU(0.2),
                input_shape=(256, 256, channels),
            ),
            # keras.layers.BatchNormalization(),
            keras.layers.Conv2D(
                32,
                kernel_size=4,
                strides=2,
                padding="SAME",
                activation=keras.layers.LeakyReLU(0.2),
            ),
            # keras.layers.BatchNormalization(),
            keras.layers.Conv2D(
                32,
                kernel_size=4,
                strides=2,
                padding="SAME",
                activation=keras.layers.LeakyReLU(0.2),
            ),
            # keras.layers.BatchNormalization(),
            keras.layers.Conv2D(
                32,
                kernel_size=3,
                strides=1,
                padding="SAME",
                activation=keras.layers.LeakyReLU(0.2),
            ),
            # keras.layers.BatchNormalization(),
            keras.layers.Conv2D(
                64,
                kernel_size=4,
                strides=2,
                padding="SAME",
                activation=keras.layers.LeakyReLU(0.2),
            ),
            # keras.layers.BatchNormalization(),
            keras.layers.Conv2D(
                64,
                kernel_size=3,
                strides=1,
                padding="SAME",
                activation=keras.layers.LeakyReLU(0.2),
            ),
            # keras.layers.BatchNormalization(),
            keras.layers.Conv2D(
                128,
                kernel_size=4,
                strides=2,
                padding="SAME",
                activation=keras.layers.LeakyReLU(0.2),
            ),  # CONV6
            # keras.layers.BatchNormalization(),
            keras.layers.Conv2D(
                64,
                kernel_size=3,
                strides=1,
                padding="SAME",
                activation=keras.layers.LeakyReLU(0.2),
            ),
            # keras.layers.BatchNormalization(),
            keras.layers.Conv2D(
                32,
                kernel_size=3,
                strides=1,
                padding="SAME",
                activation=keras.layers.LeakyReLU(0.2),
            ),
            # keras.layers.BatchNormalization(),
            keras.layers.Conv2D(
                100, kernel_size=8, strides=1, padding="VALID", activation="relu"
            ),
            # keras.layers.BatchNormalization(),
            # keras.layers.Flatten(),
        ]
    )

    conv_decoder = keras.models.Sequential(
        [
            # keras.layers.InputLayer(input_shape=(1, 1, 100)),
            keras.layers.Conv2DTranspose(
                32,
                kernel_size=3,
                strides=8,
                padding="VALID",
                # activation="relu",
                activation=keras.layers.LeakyReLU(0.2),
                input_shape=(1, 1, 100),
            ),
            # keras.layers.BatchNormalization(),
            keras.layers.Conv2DTranspose(
                64,
                kernel_size=3,
                strides=1,
                padding="SAME",
                activation=keras.layers.LeakyReLU(0.2),
            ),
            # keras.layers.BatchNormalization(),
            keras.layers.Conv2DTranspose(
                128,
                kernel_size=4,
                strides=1,
                padding="SAME",
                activation=keras.layers.LeakyReLU(0.2),
            ),
            # keras.layers.BatchNormalization(),
            keras.layers.Conv2DTranspose(
                64,
                kernel_size=3,
                strides=2,
                padding="SAME",
                activation=keras.layers.LeakyReLU(0.2),
            ),
            # keras.layers.BatchNormalization(),
            keras.layers.Conv2DTranspose(
                64,
                kernel_size=4,
                strides=1,
                padding="SAME",
                activation=keras.layers.LeakyReLU(0.2),
            ),
            # keras.layers.BatchNormalization(),
            keras.layers.Conv2DTranspose(
                32,
                kernel_size=3,
                strides=2,
                padding="SAME",
                activation=keras.layers.LeakyReLU(0.2),
            ),
            # keras.layers.BatchNormalization(),
            keras.layers.Conv2DTranspose(
                32,
                kernel_size=4,
                strides=1,
                padding="SAME",
                activation=keras.layers.LeakyReLU(0.2),
            ),
            # keras.layers.BatchNormalization(),
            keras.layers.Conv2DTranspose(
                32,
                kernel_size=4,
                strides=2,
                padding="SAME",
                activation=keras.layers.LeakyReLU(0.2),
            ),
            # keras.layers.BatchNormalization(),
            keras.layers.Conv2DTranspose(
                32,
                kernel_size=4,
                strides=2,
                padding="SAME",
                activation=keras.layers.LeakyReLU(0.2),
            ),
            # keras.layers.BatchNormalization(),
            keras.layers.Conv2DTranspose(
                channels,
                kernel_size=4,
                strides=2,
                padding="SAME",
                # activation=keras.layers.LeakyReLU(0.2),
                activation="sigmoid",  # sigmoid
            ),
        ]
    )
    model = keras.models.Sequential([conv_encoder, conv_decoder])
    print(conv_encoder.summary())
    print(conv_decoder.summary())
    print(model.summary())

    return model
