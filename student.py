#!/usr/bin/env python3
"""
z5204754

Question:
- chose to use LSTM
    - thought long term memory was useful
    - given that the inputs are sentences, the context of a word within a sentence greatly affects
        the meaning of it and its more about finding the 'tone' of the review
    - more complicated but allowed for more refinement

- ignore padded inputs
- preprocessing:
    - removing punctuation
    - removing special characters
- dropout
- remove common and uncommon words i.e. stop words
- fiddling with num of hidden nodes, learning rate, momentum
- attempted to use a regression model using MSELoss instead of classification with CrossEntropy
    and noticed that the network was less likely to make a prediction further away (i.e. 3 or 4 stars away),
    it was also less likely to correctly predict and more likely to predict one star away, reducing the overall
    weighted score.

"""

"""
student.py

UNSW COMP9444 Neural Networks and Deep Learning

You may modify this file however you wish, including creating
additional variables, functions, classes, etc., so long as your code
runs with the hw2main.py file unmodified, and you are only using the
approved packages.

You have been given some default values for the variables stopWords,
wordVectors(dim), trainValSplit, batchSize, epochs, and optimiser.
You are encouraged to modify these to improve the performance of your model.

The variable device may be used to refer to the CPU/GPU being used by PyTorch.

You may only use GloVe 6B word vectors as found in the torchtext package.
"""

import torch
import torch.nn as tnn
import torch.optim as toptim
from sklearn.feature_extraction import text
from torchtext.vocab import GloVe
from nltk.stem.porter import PorterStemmer
from torch.nn.utils.rnn import pad_sequence
import torch.nn.functional as F
# import numpy as np
# import sklearn

# TODO check if can use the below packages
import re
import string


###########################################################################
### The following determines the processing of input data (review text) ###
###########################################################################


def preprocessing(sample):
    """
    Called after tokenising but before numericalising.
    """
    # Remove punctuation, special characters
    input = " ".join(sample)
    text = re.sub(r"[^\x00-\x7F]+", " ", input)
    regex = re.compile('[' + re.escape(string.punctuation) + '0-9\\r\\t\\n]')  # remove punctuation and numbers
    nopunct = regex.sub(" ", text.lower())
    result = nopunct.split(" ")
    result = list(filter(lambda x: x != '', result))
    #stemmer = PorterStemmer()
    #result = [stemmer.stem(token) for token in result]

    #print(result)
    return result


def postprocessing(batch, vocab):
    """
    Called after numericalisation but before vectorisation.
    """
    # Remove infrequent words from batch
    vocabCount = vocab.freqs
    vocabITOS = vocab.itos

    for i, x in enumerate(batch):
        for j, y in enumerate(x):
            if vocabCount[vocabITOS[y]] < 3:
                x[j] = 0
    return batch


# stopWords = {text.ENGLISH_STOP_WORDS}

stopWords = {}

max_vocab = 150
wordVectorDimension = 200
wordVectors = GloVe(name='6B', dim=wordVectorDimension, max_vectors= max_vocab)


###########################################################################
##### The following determines the processing of label data (ratings) #####
###########################################################################


def convertLabel(datasetLabel):
    """
    Labels (product ratings) from the dataset are provided to you as
    floats, taking the values 1.0, 2.0, 3.0, 4.0, or 5.0.
    You may wish to train with these as they are, or you you may wish
    to convert them to another representation in this function.
    Consider regression vs classification.
    """
    # Convert
    out = datasetLabel.long() - 1
    return out


def convertNetOutput(netOutput):
    """
    Your model will be assessed on the predictions it makes, which
    must be in the same format as the dataset labels.  The predictions
    must be floats, taking the values 1.0, 2.0, 3.0, 4.0, or 5.0.
    If your network outputs a different representation or any float
    values other than the five mentioned, convert the output here.
    """
    out = (torch.argmax(netOutput, dim=1) + 1).float()
    return out


###########################################################################
################### The following determines the model ####################
###########################################################################


class network(tnn.Module):
    """
    Class for creating the neural network.  The input to your network
    will be a batch of reviews (in word vector form).  As reviews will
    have different numbers of words in them, padding has been added to the
    end of the reviews so we can form a batch of reviews of equal length.
    """

    def __init__(self):
        super(network, self).__init__()

        hidden_dim = 200
        num_layers = 1
        out_dim = 5
        drop_rate = 0.2

        self.conv1 = tnn.Conv1d(max_vocab, 128,5)

        self.pool1 = tnn.MaxPool1d(5) #drop resultion to allow for more filter layers

        """self.conv2 = tnn.Conv1D(128, 128, 5)

        self.pool2 = tnn.MaxPool1d(5) #drop resultion to allow for more filter layers

        self.conv3 = tnn.Conv1D(128, 128, 5)

        self.pool3 = tnn.MaxPool1d(35) #drop resultion to allow for more filter layers
        

        self.dense = tnn.Linear(45, out_dim)"""
        

        self.lstm = tnn.LSTM(input_size=wordVectorDimension, hidden_size=hidden_dim, num_layers=num_layers, batch_first=True)
        self.linear = tnn.Linear(in_features=num_layers * hidden_dim, out_features=out_dim)
        self.dropout = tnn.Dropout(drop_rate)

    def forward(self, input, length):
        #add CNN, add batch normalisation
        print("shape: ", input.shape)
        #input_pad = pad_sequence([input])
        #print("shape_pad: ", input_pad.shape)
        input = F.pad(input, (0, 0, 0 ,max_vocab - input.shape[1] ) ,"constant",0)
        print("shape: ", input.shape)

        embedded = self.dropout(input)
        embedded = tnn.utils.rnn.pack_padded_sequence(embedded, length, batch_first=True, enforce_sorted=True)
        print(embedded.data.shape)
    
        output, (hidden, cell) = self.lstm(embedded)

        # hidden = torch.cat((hidden[-2, :, :], hidden[-1, :, :]), dim=1)
        hidden = hidden[-1]

        outputs = self.linear(hidden)
        outputs = torch.softmax(outputs, dim = 1)
        return outputs


net = network()
"""
    Loss function for the model. You may use loss functions found in
    the torch package, or create your own with the loss class above.
"""
lossFunc = tnn.CrossEntropyLoss()

###########################################################################
################ The following determines training options ################
###########################################################################

trainValSplit = 0.8
batchSize = 32
epochs = 10
optimiser = toptim.SGD(net.parameters(), lr=0.08, momentum=0.8)
