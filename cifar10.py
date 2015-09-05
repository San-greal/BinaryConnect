# Copyright 2015 Matthieu Courbariaux

# This file is part of BinaryConnect.

# BinaryConnect is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# BinaryConnect is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with BinaryConnect.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import print_function

import sys
import os
import time

import numpy as np
np.random.seed(1234)  # for reproducibility

# specifying the gpu to use
# import theano.sandbox.cuda
# theano.sandbox.cuda.use('gpu1') 
import theano
import theano.tensor as T

import lasagne

import cPickle as pickle
import gzip

import batch_norm
import binary_connect

from pylearn2.datasets.zca_dataset import ZCA_Dataset    
# from pylearn2.datasets.svhn import SVHN
from pylearn2.utils import serial

if __name__ == "__main__":
    
    # BN parameters
    batch_size = 100
    print("batch_size = "+str(batch_size))
    # alpha is the exponential moving average factor
    # alpha = .1 # for a minibatch of size 50
    alpha = .2 # for a minibatch of size 100
    print("alpha = "+str(alpha))
    # alpha = .33 # for a minibatch of size 200
    epsilon = 1e-4
    print("epsilon = "+str(epsilon))
    
    # Training parameters
    num_epochs = 300
    print("num_epochs = "+str(num_epochs))
    
    # BinaryConnect    
    binary = True
    print("binary = "+str(binary))
    stochastic = True
    print("stochastic = "+str(stochastic))
    # H = (1./(1<<4))/10
    # H = 1./(1<<4)
    # H = .316
    # H = 1.
    
    # LR decay
    LR_start = 3.
    print("LR_start = "+str(LR_start))
    LR_fin = .01 
    print("LR_fin = "+str(LR_fin))
    LR_decay = (LR_fin/LR_start)**(1./num_epochs)
    # BTW, LR decay is good for the BN moving average...
    
    print('Loading CIFAR-10 dataset...')
    
    preprocessor = serial.load("${PYLEARN2_DATA_PATH}/cifar10/pylearn2_gcn_whitened/preprocessor.pkl")
    train_set = ZCA_Dataset(
        preprocessed_dataset=serial.load("${PYLEARN2_DATA_PATH}/cifar10/pylearn2_gcn_whitened/train.pkl"), 
        preprocessor = preprocessor,
        start=0, stop = 45000)
    valid_set = ZCA_Dataset(
        preprocessed_dataset= serial.load("${PYLEARN2_DATA_PATH}/cifar10/pylearn2_gcn_whitened/train.pkl"), 
        preprocessor = preprocessor,
        start=45000, stop = 50000)  
    test_set = ZCA_Dataset(
        preprocessed_dataset= serial.load("${PYLEARN2_DATA_PATH}/cifar10/pylearn2_gcn_whitened/test.pkl"), 
        preprocessor = preprocessor)
        
    # bc01 format
    # print train_set.X.shape
    train_set.X = train_set.X.reshape(-1,3,32,32)
    valid_set.X = valid_set.X.reshape(-1,3,32,32)
    test_set.X = test_set.X.reshape(-1,3,32,32)
    
    # flatten targets
    train_set.y = np.hstack(train_set.y)
    valid_set.y = np.hstack(valid_set.y)
    test_set.y = np.hstack(test_set.y)
    
    # Onehot the targets
    train_set.y = np.float32(np.eye(10)[train_set.y])    
    valid_set.y = np.float32(np.eye(10)[valid_set.y])
    test_set.y = np.float32(np.eye(10)[test_set.y])
    
    # for hinge loss
    train_set.y = 2* train_set.y - 1.
    valid_set.y = 2* valid_set.y - 1.
    test_set.y = 2* test_set.y - 1.

    print('Building the CNN...') 
    
    # Prepare Theano variables for inputs and targets
    input = T.tensor4('inputs')
    target = T.matrix('targets')
    LR = T.scalar('LR', dtype=theano.config.floatX)

    cnn = lasagne.layers.InputLayer(
            shape=(None, 3, 32, 32),
            input_var=input)
    
    # 128C3-128C3-P2    
    
    cnn = binary_connect.Conv2DLayer(
            cnn, 
            binary=binary,
            stochastic=stochastic,
            # H=H,
            num_filters=128, 
            filter_size=(3, 3),
            nonlinearity=lasagne.nonlinearities.identity)
    
    cnn = batch_norm.BatchNormLayer(
            cnn,
            epsilon=epsilon, 
            alpha=alpha,
            nonlinearity=lasagne.nonlinearities.rectify)
    
    cnn = binary_connect.Conv2DLayer(
            cnn, 
            binary=binary,
            stochastic=stochastic,
            # H=H,
            num_filters=128, 
            filter_size=(3, 3),
            nonlinearity=lasagne.nonlinearities.identity)
    
    cnn = lasagne.layers.MaxPool2DLayer(cnn, pool_size=(2, 2))
    
    cnn = batch_norm.BatchNormLayer(
            cnn,
            epsilon=epsilon, 
            alpha=alpha,
            nonlinearity=lasagne.nonlinearities.rectify)
    
    # 256C2-256C2-P2
    
    cnn = binary_connect.Conv2DLayer(
            cnn, 
            binary=binary,
            stochastic=stochastic,
            # H=H,
            num_filters=256, 
            filter_size=(2, 2),
            nonlinearity=lasagne.nonlinearities.identity)
    
    cnn = batch_norm.BatchNormLayer(
            cnn,
            epsilon=epsilon, 
            alpha=alpha,
            nonlinearity=lasagne.nonlinearities.rectify)
    
    cnn = binary_connect.Conv2DLayer(
            cnn, 
            binary=binary,
            stochastic=stochastic,
            # H=H,
            num_filters=256, 
            filter_size=(2, 2),
            nonlinearity=lasagne.nonlinearities.identity)
    
    cnn = lasagne.layers.MaxPool2DLayer(cnn, pool_size=(2, 2))
    
    cnn = batch_norm.BatchNormLayer(
            cnn,
            epsilon=epsilon, 
            alpha=alpha,
            nonlinearity=lasagne.nonlinearities.rectify)
    
    # 512C2-512C2-P2
    
    cnn = binary_connect.Conv2DLayer(
            cnn, 
            binary=binary,
            stochastic=stochastic,
            # H=H,
            num_filters=512, 
            filter_size=(2, 2),
            nonlinearity=lasagne.nonlinearities.identity)

    cnn = batch_norm.BatchNormLayer(
            cnn,
            epsilon=epsilon, 
            alpha=alpha,
            nonlinearity=lasagne.nonlinearities.rectify)
    
    cnn = binary_connect.Conv2DLayer(
            cnn, 
            binary=binary,
            stochastic=stochastic,
            # H=H,
            num_filters=512, 
            filter_size=(2, 2),
            nonlinearity=lasagne.nonlinearities.identity)
    
    cnn = lasagne.layers.MaxPool2DLayer(cnn, pool_size=(2, 2))
    
    cnn = batch_norm.BatchNormLayer(
            cnn,
            epsilon=epsilon, 
            alpha=alpha,
            nonlinearity=lasagne.nonlinearities.rectify)    
    
    # 1024C2-1024FC-10FC
    cnn = binary_connect.Conv2DLayer(
            cnn, 
            binary=binary,
            stochastic=stochastic,
            # H=H,
            num_filters=1024, 
            filter_size=(2, 2),
            nonlinearity=lasagne.nonlinearities.identity)
    
    # print(cnn.output_shape)
    
    cnn = batch_norm.BatchNormLayer(
            cnn,
            epsilon=epsilon, 
            alpha=alpha,
            nonlinearity=lasagne.nonlinearities.rectify)
    
    cnn = binary_connect.DenseLayer(
                cnn, 
                binary=binary,
                stochastic=stochastic,
                # H=H,
                nonlinearity=lasagne.nonlinearities.identity,
                num_units=1024)      
                  
    cnn = batch_norm.BatchNormLayer(
            cnn,
            epsilon=epsilon, 
            alpha=alpha,
            nonlinearity=lasagne.nonlinearities.rectify)
    
    cnn = binary_connect.DenseLayer(
                cnn, 
                binary=binary,
                stochastic=stochastic,
                # H=H,
                nonlinearity=lasagne.nonlinearities.identity,
                num_units=10)      
                  
    cnn = batch_norm.BatchNormLayer(
            cnn,
            epsilon=epsilon, 
            alpha=alpha,
            nonlinearity=lasagne.nonlinearities.identity)

    train_output = lasagne.layers.get_output(cnn, deterministic=False)
    
    # squared hinge loss
    loss = T.mean(T.sqr(T.maximum(0.,1.-target*train_output)))
    
    params = lasagne.layers.get_all_params(cnn, trainable=True)
    
    if binary:
        grads = binary_connect.compute_grads(loss,cnn)
        # updates = lasagne.updates.adam(loss_or_grads=grads, params=params, learning_rate=LR)
        updates = lasagne.updates.sgd(loss_or_grads=grads, params=params, learning_rate=LR)
        # updates = binary_connect.weights_clipping(updates,H) 
        updates = binary_connect.weights_clipping(updates,cnn) 
        # using 2H instead of H with stochastic yields about 20% relative worse results
        
    else:
        # updates = lasagne.updates.adam(loss_or_grads=loss, params=params, learning_rate=LR)
        updates = lasagne.updates.sgd(loss_or_grads=loss, params=params, learning_rate=LR)
        # updates = lasagne.updates.nesterov_momentum(loss, params, learning_rate=0.01, momentum=0.9)

    test_output = lasagne.layers.get_output(cnn, deterministic=True)
    test_loss = T.mean(T.sqr(T.maximum(0.,1.-target*test_output)))
    test_err = T.mean(T.neq(T.argmax(test_output, axis=1), T.argmax(target, axis=1)),dtype=theano.config.floatX)
    
    # Compile a function performing a training step on a mini-batch (by giving the updates dictionary) 
    # and returning the corresponding training loss:
    train_fn = theano.function([input, target, LR], loss, updates=updates)
    # train_fn = theano.function([input, target], loss, updates=updates)

    # Compile a second function computing the validation loss and accuracy:
    val_fn = theano.function([input, target], [test_loss, test_err])

    print('Training...')
    
    binary_connect.train(
            train_fn,val_fn,
            batch_size,
            LR_start,LR_decay,
            num_epochs,
            train_set.X,train_set.y,
            valid_set.X,valid_set.y,
            test_set.X,test_set.y)
    
    # print("display histogram")
    
    # W = lasagne.layers.get_all_layers(mlp)[2].W.get_value()
    # print(W.shape)
    
    # histogram = np.histogram(W,bins=1000,range=(-1.1,1.1))
    # np.savetxt(str(dropout_hidden)+str(binary)+str(stochastic)+str(H)+"_hist0.csv", histogram[0], delimiter=",")
    # np.savetxt(str(dropout_hidden)+str(binary)+str(stochastic)+str(H)+"_hist1.csv", histogram[1], delimiter=",")
    
    # Optionally, you could now dump the network weights to a file like this:
    # np.savez('model.npz', lasagne.layers.get_all_param_values(network))