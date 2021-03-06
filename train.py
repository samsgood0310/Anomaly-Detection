#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Dec 10 19:46:17 2019

@author: adnene33
"""
import os
import sys

import tensorflow as tf
from tensorflow import keras
import keras.backend as K
from modules import loss_functions as loss_functions
from modules import metrics as custom_metrics

import modules.models.mvtec as mvtec
import modules.models.mvtec_2 as mvtec_2
import modules.models.resnet as resnet

# from modules.resmaps import calculate_resmaps as calculate_resmaps

from modules import utils as utils
from keras.preprocessing.image import ImageDataGenerator
import numpy as np

import requests
import matplotlib.image as mpimg
import matplotlib.pyplot as plt

import datetime
import csv
import pandas as pd
import json

import argparse

"""
Valid input arguments for color_mode and loss:

                        +----------------+----------------+
                        |       Model Architecture        |  
                        +----------------+----------------+
                        | mvtec, mvtec2  | Resnet, Nasnet |
========================+================+================+
        ||              |                |                |
        ||   grayscale  | SSIM, L2, MSE  |   Not Valid    |
Color   ||              |                |                |
Mode    ----------------+----------------+----------------+
        ||              |                |                |
        ||      RGB     | MSSIM, L2, MSE | MSSIM, L2, MSE |
        ||              |                |                |
--------+---------------+----------------+----------------+
"""


def main(args):
    # ========================= SETUP ==============================
    # Get training data setup
    directory = args.directory
    train_data_dir = os.path.join(directory, "train")
    nb_training_images_aug = args.images
    batch_size = args.batch
    color_mode = args.color
    loss = args.loss.upper()
    validation_split = 0.1
    architecture = args.architecture
    tag = args.tag

    # check input arguments
    if architecture == "resnet" and color_mode == "grayscale":
        raise ValueError("ResNet expects rgb images")
    if architecture == "nasnet" and color_mode == "grayscale":
        raise ValueError("NasNet expects rgb images")
    if loss == "MSSIM" and color_mode == "grayscale":
        raise ValueError("MSSIM works only with rgb images")
    if loss == "SSIM" and color_mode == "rgb":
        raise ValueError("SSIM works only with grayscale images")

    # set chennels and metrics to monitor training
    if color_mode == "grayscale":
        channels = 1
        resmaps_mode = "SSIM"
        metrics = [custom_metrics.ssim_metric]
    elif color_mode == "rgb":
        channels = 3
        resmaps_mode = "MSSIM"
        metrics = [custom_metrics.mssim_metric]

    # build model
    if architecture == "mvtec":
        model = mvtec.build_model(channels)
    elif architecture == "mvtec2":
        model = mvtec_2.build_model(channels)
    elif architecture == "resnet":
        model, base_encoder = resnet.build_model()
    elif architecture == "nasnet":
        raise Exception("Nasnet ist not yet implemented.")
        # model, base_encoder = models.build_nasnet()
        # sys.exit()

    # set loss function
    if loss == "SSIM":
        loss_function = loss_functions.ssim_loss
    elif loss == "MSSIM":
        loss_function = loss_functions.mssim_loss
    elif loss == "L2":
        loss_function = loss_functions.l2_loss
    elif loss == "MSE":
        loss_function = "mean_squared_error"

    # specify model name and directory to save model
    now = datetime.datetime.now().strftime("%d-%m-%Y_%H-%M-%S")
    save_dir = os.path.join(
        os.getcwd(), "saved_models", directory, architecture, loss, now
    )
    if not os.path.isdir(save_dir):
        os.makedirs(save_dir)
    model_name = "CAE_" + architecture + "_b{}".format(batch_size)
    model_path = os.path.join(save_dir, model_name + ".h5")

    # specify logging directory for tensorboard visualization
    log_dir = os.path.join(save_dir, "logs")
    if not os.path.isdir(log_dir):
        os.makedirs(log_dir)

    # set callbacks
    early_stopping_cb = keras.callbacks.EarlyStopping(
        monitor="val_loss", patience=12, mode="min", verbose=1,
    )
    checkpoint_cb = keras.callbacks.ModelCheckpoint(
        filepath=model_path,
        monitor="val_loss",
        verbose=1,
        save_best_only=False,  # True
        save_weights_only=False,
        period=1,
    )
    tensorboard_cb = keras.callbacks.TensorBoard(
        log_dir=log_dir, write_graph=True, update_freq="epoch"
    )

    # ============================= PREPROCESSING ===============================

    if architecture in ["mvtec", "mvtec2"]:
        rescale = 1.0 / 255
        shape = (256, 256)
        preprocessing_function = None
        preprocessing = None
    elif architecture == "resnet":
        rescale = None
        shape = (299, 299)
        preprocessing_function = keras.applications.inception_resnet_v2.preprocess_input
        preprocessing = "keras.applications.inception_resnet_v2.preprocess_input"
    elif architecture == "nasnet":
        rescale = None
        shape = (224, 224)
        preprocessing_function = keras.applications.nasnet.preprocess_input
        preprocessing = "keras.applications.inception_resnet_v2.preprocess_input"
        pass

    print("[INFO] Using Keras's flow_from_directory method...")
    # This will do preprocessing and realtime data augmentation:
    train_datagen = ImageDataGenerator(
        # randomly rotate images in the range (degrees, 0 to 180)
        rotation_range=5,
        # randomly shift images horizontally (fraction of total width)
        width_shift_range=0.05,
        # randomly shift images vertically (fraction of total height)
        height_shift_range=0.05,
        # set mode for filling points outside the input boundaries
        fill_mode="nearest",
        # value used for fill_mode = "constant"
        cval=0.0,
        # randomly change brightness (darker < 1 < brighter)
        brightness_range=[0.95, 1.05],
        # set rescaling factor (applied before any other transformation)
        rescale=rescale,
        # set function that will be applied on each input
        preprocessing_function=preprocessing_function,
        # image data format, either "channels_first" or "channels_last"
        data_format="channels_last",
        # fraction of images reserved for validation (strictly between 0 and 1)
        validation_split=validation_split,
    )

    # For validation dataset, only rescaling
    validation_datagen = ImageDataGenerator(
        rescale=rescale,
        data_format="channels_last",
        validation_split=validation_split,
        preprocessing_function=preprocessing_function,
    )

    # Generate training batches with datagen.flow_from_directory()
    train_generator = train_datagen.flow_from_directory(
        directory=train_data_dir,
        target_size=shape,
        color_mode=color_mode,
        batch_size=batch_size,
        class_mode="input",
        subset="training",
        shuffle=True,
    )

    # Generate validation batches with datagen.flow_from_directory()
    validation_generator = validation_datagen.flow_from_directory(
        directory=train_data_dir,
        target_size=shape,
        color_mode=color_mode,
        batch_size=batch_size,
        class_mode="input",
        subset="validation",
        shuffle=True,
    )

    # Print command to paste in browser for visualizing in Tensorboard
    print("\ntensorboard --logdir={}\n".format(log_dir))

    # calculate epochs
    epochs = nb_training_images_aug // train_generator.samples

    # =============================== TRAINING =================================

    if architecture in ["mvtec", "mvtec2"]:

        learning_rate = 2e-3  # initialy 2e-4
        decay = 1e-4  # initialy 1e-5

        optimizer = keras.optimizers.Adam(
            learning_rate=learning_rate, beta_1=0.9, beta_2=0.999, decay=decay
        )

        model.compile(
            loss=loss_function, optimizer=optimizer, metrics=metrics,
        )

        # Fit the model on the batches generated by datagen.flow_from_directory()
        history = model.fit_generator(
            generator=train_generator,
            epochs=epochs,
            steps_per_epoch=train_generator.samples // batch_size,
            validation_data=validation_generator,
            validation_steps=validation_generator.samples // batch_size,
            # callbacks=[checkpoint_cb],
        )
        history = history.history

    elif architecture in ["resnet", "nasnet"]:

        # Phase 1: train the decoder with frozen encoder
        epochs_1 = int(np.ceil(0.7 * epochs))

        for layer in base_encoder.layers:
            layer.trainable = False

        # print(base_encoder.summary())
        print(model.summary())

        learning_rate_1 = 2e-4
        decay_1 = 1e-5

        optimizer = keras.optimizers.Adam(
            learning_rate=learning_rate_1, beta_1=0.9, beta_2=0.999, decay=decay_1
        )

        model.compile(
            loss=loss_function, optimizer=optimizer, metrics=metrics,
        )

        # Fit the model on the batches generated by datagen.flow_from_directory()
        history_1 = model.fit_generator(
            generator=train_generator,
            epochs=epochs_1,  #
            steps_per_epoch=train_generator.samples // batch_size,
            validation_data=validation_generator,
            validation_steps=validation_generator.samples // batch_size,
            # callbacks=[checkpoint_cb],
        )

        # Phase 2: train both encoder and decoder together
        epochs_2 = epochs - epochs_1

        for layer in base_encoder.layers:
            layer.trainable = True

        # print(base_encoder.summary())
        print(model.summary())

        # learning_rate_2 = 1e-5
        # decay_2 = 1e-6

        # optimizer = keras.optimizers.Adam(
        #     learning_rate=learning_rate_2, beta_1=0.9, beta_2=0.999, decay=decay_2
        # )

        model.compile(
            loss=loss_function, optimizer=optimizer, metrics=metrics,
        )

        # train for the remaining epochs
        history_2 = model.fit_generator(
            generator=train_generator,
            epochs=epochs_2,  #
            steps_per_epoch=train_generator.samples // batch_size,
            validation_data=validation_generator,
            validation_steps=validation_generator.samples // batch_size,
            # callbacks=[checkpoint_cb],
        )

        # wrap training hyper-parameters of both phases
        epochs = [epochs_1, epochs_2]
        learning_rate = [learning_rate_1, learning_rate_2]
        decay = [decay_1, decay_2]
        history = utils.extend_dict(history_1.history, history_2.history)

    # Save model
    tf.keras.models.save_model(
        model, model_path, include_optimizer=True, save_format="h5"
    )
    print("Saved trained model at %s " % model_path)

    # save training history
    hist_df = pd.DataFrame(history)
    hist_csv_file = os.path.join(save_dir, "history.csv")
    with open(hist_csv_file, mode="w") as f:
        hist_df.to_csv(f)
    print("Saved training history at %s " % hist_csv_file)

    # save plot of loss and val_loss
    plt.style.use("seaborn-darkgrid")
    plot = hist_df[["loss", "val_loss"]].plot(figsize=(8, 5))
    fig = plot.get_figure()
    fig.savefig(os.path.join(save_dir, "train_val_losses.png"))
    print("Saved training history at {} ".format(save_dir))

    epochs_trained = utils.get_epochs_trained(history)

    # save training setup and model configuration
    setup = {
        "data_setup": {
            "directory": directory,
            "nb_training_images": train_generator.samples,
            "nb_validation_images": validation_generator.samples,
        },
        "preprocessing_setup": {
            "rescale": rescale,
            "shape": shape,
            "preprocessing": preprocessing,
        },
        "train_setup": {
            "architecture": architecture,
            "nb_training_images_aug": nb_training_images_aug,
            "epochs": epochs,
            "learning_rate": learning_rate,
            "decay": decay,
            "batch_size": batch_size,
            "loss": loss,
            "color_mode": color_mode,
            "channels": channels,
            "validation_split": validation_split,
            "epochs_trained": epochs_trained,
        },
        "tag": tag,
    }

    with open(os.path.join(save_dir, "setup.json"), "w") as json_file:
        json.dump(setup, json_file, indent=4, sort_keys=False)

    # predict on validation images, compute resmaps and save for visual inspection
    inspection_generator = validation_datagen.flow_from_directory(
        directory=train_data_dir,
        target_size=shape,
        color_mode=color_mode,
        batch_size=validation_generator.samples,
        class_mode="input",
        subset="validation",
        shuffle=False,
    )
    imgs_val_input = validation_generator.next()[0]
    filenames = validation_generator.filenames
    imgs_val_pred = model.predict(imgs_val_input)
    # resmaps_val = calculate_resmaps(
    #     imgs_val_input, imgs_val_pred, loss=resmaps_mode)

    # if color_mode == "rgb":
    #     resmaps_val = tf.image.rgb_to_grayscale(resmaps_val)

    inspection_dir = os.path.join(save_dir, "inspection")
    if not os.path.isdir(inspection_dir):
        os.makedirs(inspection_dir)
    utils.save_images(inspection_dir, imgs_val_pred,
                      filenames, color_mode, "pred")
    # utils.save_images(inspection_dir, resmaps, filenames, color_mode, "resmap")


if __name__ == "__main__":
    # create parser
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-d",
        "--directory",
        type=str,
        required=True,
        metavar="",
        help="training directory",
    )

    parser.add_argument(
        "-a",
        "--architecture",
        type=str,
        required=True,
        metavar="",
        choices=["mvtec", "mvtec2", "resnet", "nasnet"],
        help="model to use in training",
    )

    parser.add_argument(
        "-i",
        "--images",
        type=int,
        default=10000,
        metavar="",
        help="number of training images",
    )
    parser.add_argument(
        "-b", "--batch", type=int, required=True, metavar="", help="batch size"
    )
    parser.add_argument(
        "-l",
        "--loss",
        type=str,
        required=True,
        metavar="",
        choices=["mssim", "ssim", "l2", "mse"],
        help="loss function used during training",
    )

    parser.add_argument(
        "-c",
        "--color",
        type=str,
        required=True,
        metavar="",
        choices=["rgb", "grayscale"],
        help="color mode",
    )

    parser.add_argument(
        "-t", "--tag", type=str, help="give a tag to the model to be trained"
    )

    args = parser.parse_args()
    if tf.test.is_gpu_available():
        print("[INFO] GPU was detected...")
    else:
        print("[INFO] No GPU was detected. CNNs can be very slow without a GPU...")
    print("[INFO] Tensorflow version: {} ...".format(tf.__version__))
    print("[INFO] Keras version: {} ...".format(keras.__version__))
    main(args)

# Examples of commands to initiate training

# python3 train.py -d mvtec/capsule -a mvtec -b 12 -l ssim -c grayscale
# python3 train.py -d mvtec/capsule -a mvtec -b 12 -l l2 -c grayscale

# python3 train.py -d werkstueck/data_a30_nikon_weiss_edit -a mvtec -b 12 -l ssim -c grayscale

# RESNET not yet supported

# python3 train.py -d mvtec/capsule -a resnet -b 12 -l mssim -c rgb
