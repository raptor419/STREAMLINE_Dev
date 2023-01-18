import os
import csv
import time
import random
import pickle
import logging
import numpy as np
from sklearn.feature_selection import mutual_info_classif
from skrebate import MultiSURF, TURF
from streamline.utils.job import Job
from streamline.utils.dataset import Dataset


class FeatureImportance(Job):
    """
    Stuff about feature importance class
    """

    def __init__(self, cv_train_path, experiment_path, class_label, instance_label, instance_subset):
        """
        Initializer for Feature Importance Job

        Args:
            cv_train_path: path for the cross-validation dataset created
            experiment_path:
            class_label:
            instance_label:
            instance_subset:
        """
        super().__init__()
        self.cv_count = None
        self.dataset = None
        self.cv_train_path = cv_train_path
        self.experiment_path = experiment_path
        self.class_label = class_label
        self.instance_label = instance_label
        self.instance_subset = instance_subset

    def run(self, algorithm, use_turf, turf_pct, random_state=42, n_jobs=-1):
        """
        Run all elements of the feature importance evaluation:
        applies either mutual information and multisurf and saves a sorted dictionary of features with associated scores

        Args:
            algorithm:
            use_turf:
            turf_pct:
            random_state:
            n_jobs:

        Returns:

        """

        self.job_start_time = time.time()
        random.seed(random_state)
        np.random.seed(random_state)
        self.prepare_data(self.cv_train_path, self.class_label, self.instance_label)
        logging.info('Prepared Train and Test for: ' + str(self.dataset.name) + "_CV_" + str(self.cv_count))

        assert (algorithm == 'MI' or algorithm == 'MS')
        # Apply mutual information if specified by user
        if algorithm == 'MI':
            logging.info('Running Mutual Information...')
            scores, output_path, alg_name = self.run_mutual_information(random_state)
        # Apply MultiSURF if specified by user
        elif algorithm == 'MS':
            logging.info('Running MultiSURF...')
            scores, output_path, alg_name = self.run_multi_surf(use_turf, turf_pct, n_jobs)
        else:
            raise Exception("Feature importance algorithm not found")

        logging.info('Sort and pickle feature importance scores...')
        # Save sorted feature importance scores:
        score_dict, score_sorted_features = self.sort_save_fi_scores(scores, output_path, output_path, alg_name)
        # Pickle feature importance information to be used in Phase 4 (feature selection)
        self.pickle_scores(alg_name, scores, score_dict, score_sorted_features)
        # Save phase runtime
        self.save_runtime(alg_name)
        # Print phase completion
        logging.info(self.dataset.name + " CV" + str(self.cv_count) + " phase 3 "
                     + alg_name + " evaluation complete")
        job_file = open(
            self.experiment_path + '/jobsCompleted/job_' + alg_name + '_'
            + self.dataset.name + '_' + str(self.cv_count) + '.txt', 'w')
        job_file.write('complete')
        job_file.close()

    def prepare_data(self, cv_train_path, class_label, instance_label):
        """
        Loads target cv training dataset, separates class from features and removes instance labels.
        """
        self.dataset = Dataset(cv_train_path, class_label, instance_label=instance_label)
        self.dataset.name = cv_train_path.split('/')[-3]
        self.dataset.instance_label = instance_label
        self.dataset.class_label = class_label
        self.cv_count = cv_train_path.split('/')[-1].split("_")[-2]

    def run_mutual_information(self, random_state):
        """
        Run mutual information on target training dataset and return scores as well as file path/name information.
        """
        alg_name = "mutual_information"
        output_path = self.experiment_path + '/' + self.dataset.name + "/feature_selection/" \
                      + alg_name + '/' + alg_name + "_scores_cv_" + str(self.cv_count) + '.csv'
        scores = mutual_info_classif(self.dataset.feature_only_data(), self.dataset.get_outcome(),
                                     random_state=random_state)
        return scores, output_path, alg_name

    def run_multi_surf(self, use_turf, turf_pct, n_jobs):
        """
        Run multiSURF (a Relief-based feature importance algorithm able to detect both univariate
        and interaction effects) and return scores as well as file path/name information
        """
        # Format instance sampled dataset (prevents MultiSURF from running a very long time in large instance spaces)
        data_features = self.dataset.feature_only_data()
        formatted = np.insert(data_features, data_features.shape[1], self.dataset.get_outcome(), 1)
        choices = np.random.choice(formatted.shape[0], min(self.instance_subset, formatted.shape[0]), replace=False)
        new_l = list()
        for i in choices:
            new_l.append(formatted[i])
        formatted = np.array(new_l)
        data_features = np.delete(formatted, -1, axis=1)
        data_phenotypes = formatted[:, -1]
        # Run MultiSURF
        alg_name = "multisurf"
        output_path = self.experiment_path + '/' + self.dataset.name + "/feature_selection/" + alg_name + "/" \
                    + alg_name + "_scores_cv_" + str(self.cv_count) + '.csv'
        if use_turf:
            try:
                clf = TURF(MultiSURF(n_jobs=n_jobs), pct=turf_pct).fit(data_features, data_phenotypes)
            except Exception:
                raise Exception("skrebate verison error")
        else:
            clf = MultiSURF(n_jobs=n_jobs).fit(data_features, data_phenotypes)
        scores = clf.feature_importances_
        return scores, output_path, alg_name

    def pickle_scores(self, output_name, scores, score_dict, score_sorted_features):
        """
        Pickle the scores, score dictionary and features sorted by score to be used primarily
        in phase 4 (feature selection) of pipeline
        """
        # Save Scores to pickled file for later use
        if not os.path.exists(self.experiment_path + '/' + self.dataset.name
                              + "/feature_selection/" + output_name + "/pickledForPhase4"):
            os.mkdir(self.experiment_path + '/' + self.dataset.name
                     + "/feature_selection/" + output_name + "/pickledForPhase4")
        outfile = open(
            self.experiment_path + '/' + self.dataset.name + "/feature_selection/" + output_name
            + "/pickledForPhase4/" + str(self.cv_count) + '.pickle', 'wb')
        pickle.dump([scores, score_dict, score_sorted_features], outfile)
        outfile.close()

    def save_runtime(self, output_name):
        """
        Save phase runtime
        Args:
            output_name: name of the output tag
        """
        runtime_file = open(
            self.experiment_path + '/' + self.dataset.name + '/runtime/runtime_' + output_name + '_CV_'
            + str(self.cv_count) + '.txt', 'w')
        runtime_file.write(str(time.time() - self.job_start_time))
        runtime_file.close()

    @staticmethod
    def sort_save_fi_scores(scores, ordered_feature_names, filename, algo_name):
        """
        Creates a feature score dictionary and a dictionary sorted by decreasing feature importance scores.

        Args:
            scores:
            ordered_feature_names:
            filename:
            algo_name:

        Returns: score_dict, score_sorted_features - dictionary of scores and score sorted name of features

        """
        # Put list of scores in dictionary
        score_dict = {}
        i = 0
        for each in ordered_feature_names:
            score_dict[each] = scores[i]
            i += 1
        # Sort features by decreasing score
        score_sorted_features = sorted(score_dict, key=lambda x: score_dict[x], reverse=True)
        # Save scores to 'formatted' file
        with open(filename, mode='w', newline="") as file:
            writer = csv.writer(file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
            writer.writerow(["Sorted " + algo_name + " Scores"])
            for k in score_sorted_features:
                writer.writerow([k, score_dict[k]])
        file.close()
        return score_dict, score_sorted_features
