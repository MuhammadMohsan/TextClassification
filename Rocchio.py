from __future__ import division
import numpy as np
import scipy as sc
from prettyprint import pp
import os
import re
from datetime import datetime as dt

#index label in the dictionary
idx_lbl = 'idx'
dfreq_lbl = "docfreq"


pattern = re.compile(r'([a-zA-Z]+|[0-9]+(\.[0-9]+)?)')

def tokenizeDoc(doc_address, min_len = 0, remove_numerics=True):
    """
    to tokenize a document file to alphabetic tokens use this function.
    doc_address: path to the file that is going to be tokenized
    min_len: minimum length of a token. Default value is zero, it should always be non-negative.
    remove_numerics: whether to remove the numeric tokens or not
    """
    from string import punctuation, digits
    tokens = []
    try:
        f = open(doc_address)
        raw = f.read().lower()
        text = pattern.sub(r' \1 ', raw.replace('\n', ' '))
        text_translated = ''
        if remove_numerics:
            text_translated = text.translate(None, punctuation + digits)
        else:
            text_translated = text.translate(None, punctuation)
        tokens = [word for word in text_translated.split(' ') if (word and len(word) > min_len)]
        f.close()
    except:
        print "Error: %s couldn't be opened!", doc_address
    finally:
        return tokens



def createDictionary(classes, tokens_pool):
    """
    this method will create a dictionary out of the tokens_pool it has been provided.
    classes: this is a list of the names of the classes documents belong to
    tokens_pool: a pool (in fact implemented as a dictionary) of tokens. Each value of the dictionary is an list of lists,
                 each list belonging to a document in the corresponding class that has a list of tokens

    output:
            *Note that the tokens in the dictionary are not sorted, since in the vector space model
             that we are going to use, all words are treated equal.
                 We practically believe in justice. Words in dictionary are tired of
                 all this injustice they have been forced to take for such a long time.
                 Now is the time to rise and earn the justice that belongs to them.
    """

    token_dict = {}
    idx = 0 #a unique index for words in dictionary
    for cl in classes:
        for tokens_list in tokens_pool[cl]:
            for token in tokens_list:
                if token in token_dict:             #if token has been added to the dictionary before
                    if cl in token_dict[token]:
                        token_dict[token][cl] += 1
                    else:
                        token_dict[token][cl] = 1
                else:
                    token_dict[token] = {}
                    token_dict[token][idx_lbl] = idx
                    idx += 1
                    token_dict[token][cl] = 1
    return token_dict



def createTokenPool(classes, paths):
    """
    this method will create a pool of tokens out of the list of paths to documents it will be provided
    classes: a list of the names of the classes documents belong to
    paths: a dictionary of lists of paths to documents

    output: a dictionary of lists of lists of tokens. each value bin of dictionary is a has a list of lists,
            for which each list is of a document and it contains a list of tokens in that document
    """
    token_pool = {}
    for cl in classes:
        token_pool[cl] = []
        for path in paths[cl]:
            token_pool[cl].append(tokenizeDoc(path))

    return token_pool



def saveDictToFile(tdict, filename):
    """
    this method will save the key/value pair of the dictionary to a csv file
    tdict: a dictionary object containing many pairs of key and value
    filename: name of the dictionary file

    output: a csv file in which dictionary is dumped
    """
    import csv
    w = csv.writer(open(filename, "w"))
    for key, val in tdict.items():
        row = []
        row.append(key)
        row.append(val[idx_lbl])
        for cl in class_titles:
            if cl in val:
                row.append(cl + ':' + str(val[cl]))
        w.writerow(row)



def readFileToDict(filename):
    """
    this method will create a dictionary from a file
    filename: name of the dictionary file
    *dictionary file is a csv file, each row contains a token and it's index

    output: a dictionary object created from input file
    """
    import csv, codecs
    tdict = {}
    for row in csv.reader(codecs.open(filename, 'r')):
        try:
            tdict[row[0]] = {}
            tdict[row[0]][idx_lbl] = int(row[1])
            for i in range(2, len(row)):
                lbl, cnt = row[i].split(':')
                tdict[row[0]][lbl] = int(cnt)
        except:
            continue
    return tdict



def train_test_split(ratio, classes, files):
    """
    this method will split the input list of files to train and test sets

    output: a tuple of train and test files after splitting

    *Note: currently this method uses the simplest way an array can be split in two parts
    """
    train_dict = {}
    test_dict = {}
    for cl in classes:
        train_cnt = int(ratio * len(files[cl]))
        train_dict[cl] = files[cl][:train_cnt]
        test_dict[cl] = files[cl][train_cnt+1:]
    return train_dict, test_dict




class Rocchio:
    """
    This is an implementation of the Rocchio classifier.
    In the training phase, this classifier will learn centroids for each class.
    After the training phase, it can easily predict the class label for a given input vector.
    By calculating the input vector's distance to each centroid, input vector's
    class label will be the label of the class having minimum distance.

    *Note: each taining set vector should be normlized to unit length, however even normalizing
           input vectors doesn't indicate that centroid vectors will have unit length.
           Nonetheless, until input vector and each training set vector are normlized, we shouldn't
           have any problems.

    lbl = argmax_{k} |\mu_{k} - v(d)|
    """
    def __init__(self, class_labels, tdict):
        """
        constructor will get a list of the class labels, a dictionary of terms (as created before).
        Then, by calling the train function, probabilities will be learned from the training set.
        class_labels: a list of class labels
        tdict: a dictionary of terms, termIDs, and number of occurences of term in each class
        """
        self.k = len(class_labels)
        # self.centroids = [np.zeros((len(tdict), 1))]*self.k # centroid vector for each class
        self.centroids = []
        self.lbl_dict = dict(zip(class_labels, range(self.k)))
        self.class_labels = class_labels
        self.tdict = tdict
        self.ctermcnt = np.zeros((self.k, 1))           # total number of terms in a class

    def train(self, token_pool, tfidf_but_smoothing = True):
        """
        this method will find the centroids for each class
        token_pool: a pool of tokens for each document in each class. We could find the centroid for
                    each class using only the dictionary provided; but the normalization is the problem.
                    This way, each training set vector can be normalized to unit length.
        tfidf_but_smoothing: if True, tfidf weighting will be used (ntn.ntn)
                             if False, smoothing will be used
        """

        if len(token_pool) != len(self.class_labels):
            print "error! number of classes don't match"
            return

        # now find the term frequency for each class
        for term, data in self.tdict.items():
            for cl in self.lbl_dict:
                if cl in data:
                    self.ctermcnt[self.lbl_dict[cl], 0] += data[cl]

        # now normalize each input vector and add it to its corresponding centroid vector
        for cl in self.class_labels:
            self.centroids.append(np.zeros((len(self.tdict), 1)))
            for doc in token_pool[cl]:
                vec = self.__createNormalizedVectorRepresentation(doc, cl)
                self.centroids[self.lbl_dict[cl]] += vec

            self.centroids[self.lbl_dict[cl]] /= len(token_pool[cl])

    def predict(self, doc):
        """
        this method will predict the label for the input document using the Rochhio's classification method
        doc: input document for which its label is going to be predicted, this argument should be provided as an array of tokens

        output: label of the document
        """

        doc_vec = self.__createNormalizedVectorRepresentation(doc, None)

        distances = []
        for i in range(self.k):
            distances.append(np.linalg.norm(doc_vec - self.centroids[i]))


        # pp (distances)

        return self.class_labels[distances.index(min(distances))]


    def predictPool(self, doc_collection):
        """
        this method will get a dictionary of collection of documents and predict their label.
        doc_collection: a dictionary of collection of documents for which we want to predict their label

        output: as output, a dictionary of collection of labels for each corresponding document will be returned
        """
        lbl_pool = {}
        for cl in self.class_labels:
            lbl_pool[cl] = []
            for doc in doc_collection[cl]:
                lbl_pool[cl].append(self.predict(doc))

        return lbl_pool


    def __createNormalizedVectorRepresentation(self, tokens_list, cl = None, tfidf = True):
        """
        this method will create a vector space representation of the list of tokens provided with unit length
        self.tdict: dictionary against which the vector space representation will be produced
        tokens_list: a list of tokens all of whom which may or may not belong to the dictionary provided
        cl: the input vector's class, in case it is None, term frequency will be calculated from the document vector itself
        output: a tfidf vector of size len(tdict)*1 that is normalized to have a unit length
        """
        vec = np.zeros((len(self.tdict), 1))
        for token in tokens_list:
            if token in self.tdict:
                vec[self.tdict[token][idx_lbl], 0] += 1

        token_set = set(tokens_list)
        if tfidf:
            if cl != None:
                for term in token_set:
                    if cl in self.tdict[term]:
                        vec[self.tdict[term][idx_lbl], 0] *= np.log(self.ctermcnt[self.lbl_dict[cl], 0] * 1.0 / self.tdict[term][cl])


        norm_vec = np.linalg.norm(vec)
        vec = (vec / (norm_vec + 1e-14))
        return vec


def calculateMetrics(class_labels, lbl_pool):
    """
    this method will calculate the tp, tn, fp, fn metrics for each class
    of documents from the pool labels provided
        tp: number of documents in the class that are correctly labeled as belonging to class
        tn: number of documents not in the class that are correctly labeled as not belonging to class
        fp: number of documents not in the class that are incorrectly labeled as belonging to class
        fn: number of documents in the class that are incorrectly labeled as not belonging to class

    class_labels: labels of the classes
    lbl_pool: a dictionary of collections of labels

    output: a dictionary of dictionaries of metrics for each class
    """
    metrics = {}
    for cl in class_labels:
        metrics[cl] = {}
        tp = 0
        tn = 0
        fp = 0
        fn = 0
        for lbl in lbl_pool[cl]:
            if lbl == cl:
                tp += 1
            else:
                fp += 1
        for ncl in class_labels:
            if ncl != cl:
                for lbl in lbl_pool[ncl]:
                    if lbl == cl:
                        fn += 1
                    else:
                        tn += 1

        metrics[cl]["tp"] = tp
        metrics[cl]["tn"] = tn
        metrics[cl]["fp"] = fp
        metrics[cl]["fn"] = fn

    return metrics


def main():

    root_path = 'E:/University Central/Modern Information Retrieval/Project/Project Phase 2/20_newsgroup/'
    #top_view folders
    folders = [root_path + folder + '/' for folder in os.listdir(root_path)]

    #there are only 4 classes
    class_titles = os.listdir(root_path)


    #list of all the files belonging to each class
    files = {}
    for folder, title in zip(folders, class_titles):
        files[title] = [folder + f for f in os.listdir(folder)]

    train_test_ratio = 0.75

    train, test = train_test_split(train_test_ratio, class_titles, files)

    pool = createTokenPool(class_titles, train)
    print len(pool[class_titles[0]])
    tdict = createDictionary(class_titles, pool)
    print len(tdict)

    print "Rocchio's turn"

    rocchio = Rocchio(class_titles, tdict)

    start = dt.now()
    rocchio.train(pool)
    end = dt.now()

    print 'elapsed time for training rocchio'
    print end - start

    for c in rocchio.centroids:
        print np.linalg.norm(c - rocchio.centroids[0])
    id = 3

    start = dt.now()
    lbl = rocchio.predict(tokenizeDoc(test[class_titles[id]][3]))
    end = dt.now()

    print 'elapsed time for testing rocchio'
    print end - start

    print lbl == class_titles[id]


    test_pool = createTokenPool(class_titles, test)
    start = dt.now()
    test_lbl_pool = rocchio.predictPool(test_pool)
    end = dt.now()

    print 'elapsed time for testing a pool of documents'
    print end - start


    metrics = calculateMetrics(class_titles, test_lbl_pool)
    total_F = 0
    for cl in class_titles:
        print cl
        P = (metrics[cl]["tp"] * 1.0 / (metrics[cl]["tp"] + metrics[cl]["fp"]))
        R = (metrics[cl]["tp"] * 1.0 / (metrics[cl]["tp"] + metrics[cl]["fn"]))
        Acc = ((metrics[cl]["tp"] + metrics[cl]["tn"])* 1.0 / (metrics[cl]["tp"] + metrics[cl]["fp"] + metrics[cl]["fn"] + metrics[cl]["tn"]))
        F_1 = 2 * R * P / (R + P)
        total_F += F_1
        print 'P = ', P
        print 'R = ', R
        print ' '

    print 'macro-averaged F measure', (total_F / len(class_titles))




    # saveDictToFile(tdict, 'dictionary.csv')
    #
    # redict = readFileToDict('dictionary.csv')
    # print len(redict)
    #
    # print redict == tdict



if __name__ == "__main__":
    main()
