import csv
import logging
import os

import pandas as pd


class Dataset:
    def __init__(self, dataset_path, class_label, match_label=None, instance_label=None):
        """
        Creates dataset with path of tabular file

        Args:
            dataset_path: path of tabular file (as csv, tsv, or txt)
            class_label: column label for the outcome to be predicted in the dataset
            match_label: column to identify unique groups of instances in the dataset \
            that have been 'matched' as part of preparing the dataset with cases and controls \
            that have been matched for some co-variates \
            Match label is really only used in the cross validation partitioning \
            It keeps any set of instances with the same match label value in the same partition.
            instance_label: Instance label is mostly used by the rule based learner in modeling, \
            we use it to trace back heterogeneous subgroups to the instances in the original dataset

        """
        self.data = None
        self.path = dataset_path
        self.name = self.path.split('/')[-1].split('.')[0]
        self.format = self.path.split('/')[-1].split('.')[-1]
        self.class_label = class_label
        self.match_label = match_label
        self.instance_label = instance_label
        self.load_data()

    def load_data(self):
        """
        Function to load data in dataset
        """
        logging.info("Loading Dataset: " + str(self.name))
        if self.format == 'csv':
            self.data = pd.read_csv(self.path, na_values='NA', sep=',')
        elif self.format == 'tsv':
            self.data = pd.read_csv(self.path, na_values='NA', sep='\t')
        elif self.format == 'txt':
            self.data = pd.read_csv(self.path, na_values='NA', sep=' ')
        else:
            raise Exception("Unknown file format")

        if not (self.class_label in self.data.columns):
            raise Exception("Class label not found in file")
        if self.match_label and not (self.match_label in self.data.columns):
            raise Exception("Match label not found in file")
        if self.instance_label and not (self.instance_label in self.data.columns):
            raise Exception("Instance label not found in file")

    def feature_only_data(self):
        """
        Create features-only version of dataset for some operations
        Returns: dataframe x_data with only features

        """

        if self.instance_label is None and self.match_label is None:
            x_data = self.data.drop([self.class_label], axis=1)  # exclude class column
        elif self.instance_label is not None and self.match_label is None:
            x_data = self.data.drop([self.class_label, self.instance_label], axis=1)  # exclude class column
        elif self.instance_label is None and self.match_label is not None:
            x_data = self.data.drop([self.class_label, self.match_label], axis=1)  # exclude class column
        else:
            x_data = self.data.drop([self.class_label, self.instance_label, self.match_label],
                                    axis=1)  # exclude class column
        return x_data

    def non_feature_data(self):
        """
        Create non features version of dataset for some operations
        Returns: dataframe y_data with only non features

        """
        if self.instance_label is None and self.match_label is None:
            y_data = self.data[[self.class_label]]
        elif self.instance_label is not None and self.match_label is None:
            y_data = self.data[[self.class_label, self.instance_label]]
        elif self.instance_label is None and self.match_label is not None:
            y_data = self.data[[self.class_label, self.match_label]]
        else:
            y_data = self.data[[self.class_label, self.instance_label, self.match_label]]
        return y_data

    def get_outcome(self):
        """
        Function to get outcome value form data
        Returns: outcome column

        """
        return self.data[self.class_label]

    def clean_data(self, ignore_features):
        """
        Basic data cleaning: Drops any instances with a missing outcome
        value as well as any features (ignore_features) specified by user
        """
        # Remove instances with missing outcome values
        self.data = self.data.dropna(axis=0, how='any', subset=[self.class_label])
        self.data = self.data.reset_index(drop=True)
        self.data[self.class_label] = self.data[self.class_label].astype(dtype='int8')
        # Remove columns to be ignored in analysis
        if ignore_features:
            self.data = self.data.drop(ignore_features, axis=1)

    def set_headers(self, experiment_path, phase='exploratory'):
        """
        Exports dataset header labels for use as a reference later in the pipeline.

        Returns: list of headers labels
        """
        # Get Original Headers
        if not os.path.exists(experiment_path + '/' + self.name + '/' + phase):
            os.makedirs(experiment_path + '/' + self.name + '/' + phase)
        headers = self.data.columns.values.tolist()
        with open(experiment_path + '/' + self.name + '/' + phase + '/OriginalFeatureNames.csv', mode='w',
                  newline="") as file:
            writer = csv.writer(file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
            writer.writerow(headers)
        return headers
