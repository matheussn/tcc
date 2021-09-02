import argparse
import os
import uuid
from glob import glob

import numpy as np
from matplotlib import pyplot
from numpy import ones
from numpy import zeros
from numpy.random import randint
from numpy.random import randn
from tensorflow.keras import Sequential, Model, Input
from tensorflow.keras.layers import Conv2D, MaxPooling2D, UpSampling2D, Concatenate, Dense, BatchNormalization, \
    LeakyReLU, Reshape, Flatten
from tensorflow.keras.layers.experimental.preprocessing import Resizing
from tensorflow.keras.preprocessing.image import load_img
from tensorflow.python.keras.optimizer_v2.adam import Adam

from utils.gpu import set_gpu_limit

BASE_DIR = f"exec_{uuid.uuid1()}"

os.mkdir(BASE_DIR)
LOG_FILE = open(f'{BASE_DIR}/logs.txt', 'a')


def get_discriminator(input_size=(250, 450, 3)):
    model = Sequential()

    model.add(Conv2D(64, 3, activation='relu', padding='same', kernel_initializer='he_normal', input_shape=input_size,
                     name="conv_2d_1"))
    model.add(Conv2D(64, 3, activation='relu', padding='same', kernel_initializer='he_normal', name="conv_2d_2"))
    model.add(MaxPooling2D(pool_size=(2, 2), name="max_pooling_2d_1"))

    model.add(Conv2D(128, 3, activation='relu', padding='same', kernel_initializer='he_normal', name="conv_2d_3"))
    model.add(Conv2D(128, 3, activation='relu', padding='same', kernel_initializer='he_normal', name="conv_2d_4"))
    model.add(MaxPooling2D(pool_size=(2, 2), name="max_pooling_2d_2"))

    model.add(Conv2D(256, 3, activation='relu', padding='same', kernel_initializer='he_normal', name="conv_2d_5"))
    model.add(Conv2D(256, 3, activation='relu', padding='same', kernel_initializer='he_normal', name="conv_2d_6"))
    model.add(MaxPooling2D(pool_size=(2, 2), name="max_pooling_2d_3"))

    model.add(Conv2D(512, 3, activation='relu', padding='same', kernel_initializer='he_normal', name="conv_2d_7"))
    model.add(Conv2D(512, 3, activation='relu', padding='same', kernel_initializer='he_normal', name="conv_2d_8"))
    model.add(MaxPooling2D(pool_size=(2, 2), name="max_pooling_2d_4"))

    model.add(Conv2D(1024, 3, activation='relu', padding='same', kernel_initializer='he_normal', name="conv_2d_9"))
    model.add(Flatten())
    model.add(Dense(1))
    return model


def get_generator(input_dim=100):
    gen_input = Input(input_dim)
    init = LeakyReLU()(BatchNormalization()(Dense(16 * 29 * 1024, input_dim=input_dim, use_bias=False)(gen_input)))
    init = Reshape((16, 29, 1024))(init)
    conv5 = Conv2D(1024, 3, activation='relu', padding='same', kernel_initializer='he_normal')(init)

    up6 = Conv2D(512, 2, activation='relu', padding='same', kernel_initializer='he_normal')(
        UpSampling2D(size=(2, 2))(conv5))
    merge6 = Concatenate(axis=3)([up6])
    conv6 = Conv2D(512, 3, activation='relu', padding='same', kernel_initializer='he_normal')(merge6)
    conv6 = Conv2D(512, 3, activation='relu', padding='same', kernel_initializer='he_normal')(conv6)

    up1 = UpSampling2D(size=(2, 2))(conv6)
    up7 = Conv2D(256, 2, activation='relu', padding='same', kernel_initializer='he_normal')(up1)
    conv3 = Conv2D(256, 3, activation='relu', padding='same', kernel_initializer='he_normal')(up1)
    merge7 = Concatenate(axis=3)([conv3, up7])
    conv7 = Conv2D(256, 3, activation='relu', padding='same', kernel_initializer='he_normal')(merge7)
    conv7 = Conv2D(256, 3, activation='relu', padding='same', kernel_initializer='he_normal')(conv7)

    up2 = UpSampling2D(size=(2, 2))(conv7)
    up8 = Conv2D(128, 2, activation='relu', padding='same', kernel_initializer='he_normal')(up2)
    conv2 = Conv2D(128, 3, activation='relu', padding='same', kernel_initializer='he_normal')(up2)
    merge8 = Concatenate(axis=3)([conv2, up8])
    conv8 = Conv2D(128, 3, activation='relu', padding='same', kernel_initializer='he_normal')(merge8)
    conv8 = Conv2D(128, 3, activation='relu', padding='same', kernel_initializer='he_normal')(conv8)

    up3 = UpSampling2D(size=(2, 2))(conv8)
    up9 = Conv2D(64, 2, activation='relu', padding='same', kernel_initializer='he_normal')(up3)
    conv1 = Conv2D(64, 3, activation='relu', padding='same', kernel_initializer='he_normal')(up3)
    merge9 = Concatenate(axis=3)([conv1, up9])
    conv9 = Conv2D(64, 3, activation='relu', padding='same', kernel_initializer='he_normal')(merge9)
    conv9 = Conv2D(64, 3, activation='relu', padding='same', kernel_initializer='he_normal')(conv9)
    conv9 = Conv2D(3, 3, activation='relu', padding='same', kernel_initializer='he_normal')(conv9)
    output = Resizing(height=250, width=450)(conv9)
    model = Model(inputs=[gen_input], outputs=[output])

    model.compile(optimizer=Adam(learning_rate=3e-4), loss='binary_crossentropy', metrics=['accuracy'])

    return model


def get_gan(disc, gen):
    disc.trainable = False
    model = Sequential(name="generator")
    model.add(gen)
    model.add(disc)
    opt = Adam(learning_rate=2e-4, beta_1=0.05)
    model.compile(loss='binary_crossentropy', optimizer=opt)
    return model


def load_real_samples(path: str):
    images_glob = glob(f'{path}*')

    train_images = []
    for img_path in images_glob:
        img = np.array(load_img(path=img_path, color_mode='rgb', target_size=(250, 450)))
        train_images.append(img)

    trainX = np.asarray(train_images)
    # convert from unsigned ints to floats
    dataset = trainX.astype('float32')
    # scale from [0,255] to [-1,1]
    dataset = (dataset - 127.5) / 127.5
    return dataset


# select real samples
def generate_real_samples(dataset, n_samples):
    # choose random instances
    ix = randint(0, dataset.shape[0], n_samples)
    # retrieve selected images
    X = dataset[ix]
    # generate 'real' class labels (1)
    y = ones((n_samples, 1))
    return X, y


# generate points in latent space as input for the generator
def generate_latent_points(latent_dim, n_samples):
    # generate points in the latent space
    x_input = randn(latent_dim * n_samples)
    # reshape into a batch of inputs for the network
    x_input = x_input.reshape(n_samples, latent_dim)
    return x_input


# use the generator to generate n fake examples, with class labels
def generate_fake_samples(g_model, latent_dim, n_samples):
    # generate points in latent space
    x_input = generate_latent_points(latent_dim, n_samples)
    # predict outputs
    X = g_model.predict(x_input)
    # create 'fake' class labels (0)
    y = zeros((n_samples, 1))
    return X, y


# create and save a plot of generated images
def save_plot(examples, epoch, n=7):
    # scale from [-1,1] to [0,1]
    examples = (examples + 1) / 2.0
    # plot images
    for i in range(n * n):
        # define subplot
        pyplot.subplot(n, n, 1 + i)
        # turn off axis
        pyplot.axis('off')
        # plot raw pixel data
        pyplot.imshow(examples[i])
    # save plot to file
    filename = f'{BASE_DIR}/generated_plot_e%03d.png' % (epoch + 1)
    pyplot.savefig(filename)
    pyplot.close()


# evaluate the discriminator, plot generated images, save generator model
def summarize_performance(epoch, g_model, d_model, dataset, latent_dim, n_samples=150):
    # prepare real samples
    X_real, y_real = generate_real_samples(dataset, n_samples)
    # evaluate discriminator on real examples
    _, acc_real = d_model.evaluate(X_real, y_real, verbose=0)
    # prepare fake examples
    x_fake, y_fake = generate_fake_samples(g_model, latent_dim, n_samples)
    # evaluate discriminator on fake examples
    _, acc_fake = d_model.evaluate(x_fake, y_fake, verbose=0)
    # summarize discriminator performance
    print('>Accuracy real: %.0f%%, fake: %.0f%%' % (acc_real * 100, acc_fake * 100), file=LOG_FILE)
    # save plot
    save_plot(x_fake, epoch)
    # save the generator model tile file
    filename = f'{BASE_DIR}/generator_model_%03d.h5' % (epoch + 1)
    g_model.save(filename)


# train the generator and discriminator
def train(g_model, d_model, gan_model, dataset, latent_dim, n_epochs=200, n_batch=128):
    bat_per_epo = int(dataset.shape[0] / 2)
    half_batch = int(n_batch / 2)
    # manually enumerate epochs
    for i in range(n_epochs):
        # enumerate batches over the training set
        for j in range(bat_per_epo):
            # get randomly selected 'real' samples
            X_real, y_real = generate_real_samples(dataset, half_batch)
            # update discriminator model weights
            d_loss1, _ = d_model.train_on_batch(X_real, y_real)
            # generate 'fake' examples
            X_fake, y_fake = generate_fake_samples(g_model, latent_dim, half_batch)
            # update discriminator model weights
            d_loss2, _ = d_model.train_on_batch(X_fake, y_fake)
            # prepare points in latent space as input for the generator
            X_gan = generate_latent_points(latent_dim, n_batch)
            # create inverted labels for the fake samples
            y_gan = ones((n_batch, 1))
            # update the generator via the discriminator's error
            g_loss = gan_model.train_on_batch(X_gan, y_gan)
            # summarize loss on this batch
            print('>%d, %d/%d, d1=%.3f, d2=%.3f g=%.3f' %
                  (i + 1, j + 1, bat_per_epo, d_loss1, d_loss2, g_loss))
            print('>%d, %d/%d, d1=%.3f, d2=%.3f g=%.3f' %
                  (i + 1, j + 1, bat_per_epo, d_loss1, d_loss2, g_loss), file=LOG_FILE)
        # evaluate the model performance, sometimes
        if (i + 1) % 10 == 0:
            summarize_performance(i, g_model, d_model, dataset, latent_dim)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument('-d', dest='dataset_path', help='path of dataset', required=True)
    args = parser.parse_args()
    set_gpu_limit()
    latent_dim = 100
    generator = get_generator()
    discriminator = get_discriminator()
    # test add , decay=1e-8
    discriminator.compile(loss='binary_crossentropy', optimizer=Adam(learning_rate=1e-3, beta_1=0.5),
                          metrics=['accuracy'])

    gan = get_gan(discriminator, generator)
    gan.compile(loss='binary_crossentropy', optimizer=Adam(learning_rate=2e-4, beta_1=0.05))

    dataset = load_real_samples(args.dataset_path)
    train(generator, discriminator, gan, dataset, latent_dim)