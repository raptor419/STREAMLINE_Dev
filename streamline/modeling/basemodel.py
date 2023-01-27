import copy
import logging
import optuna
from sklearn import clone, metrics
from sklearn.metrics import auc
from sklearn.model_selection import StratifiedKFold
from streamline.utils.evaluation import class_eval


class BaseModel:
    def __init__(self, model, model_name,
                 cv_folds=5, scoring_metric='balanced_accuracy', metric_direction='maximize',
                 random_state=None, cv=None, sampler=None):
        self.is_single = True
        self.model = model
        self.small_name = model_name.replace(" ", "_")
        self.model_name = model_name
        self.y_train = None
        self.x_train = None
        self.param_grid = None
        self.params = None
        self.random_state = random_state
        self.scoring_metric = scoring_metric
        self.metric_direction = metric_direction
        if cv is None:
            self.cv = StratifiedKFold(n_splits=cv_folds, shuffle=True, random_state=self.random_state)
        else:
            self.cv = cv

        if sampler is None:
            self.sampler = optuna.samplers.TPESampler(seed=self.random_state)
        else:
            self.sampler = sampler
        self.study = None
        optuna.logging.set_verbosity(optuna.logging.INFO)

    def objective(self, trail):
        raise NotImplementedError

    def optimize(self, x_train, y_train, n_trails, timeout):
        self.x_train = x_train
        self.y_train = y_train
        for key, value in self.param_grid.items():
            if len(value) > 1:
                self.is_single = False
                break

        if not self.is_single:
            self.study = optuna.create_study(direction=self.metric_direction, sampler=self.sampler)
            self.study.optimize(lambda trial: self.objective(trial), n_trials=n_trails, timeout=timeout,
                                catch=(ValueError,))
            logging.info('Best trial:')
            best_trial = self.study.best_trial
            logging.info('  Value: ', best_trial.value)
            logging.info('  Params: ')
            for key, value in best_trial.params.items():
                logging.info('    {}: {}'.format(key, value))
            # Specify model with optimized hyperparameters
            # Export final model hyperparamters to csv file

            self.model = self.study.best_trial
        else:
            self.params = copy.deepcopy(self.param_grid)
            for key, value in self.param_grid.items():
                self.params[key] = value[0]
            self.model = clone(self.model).set_params(**self.params)

    def feature_importance(self):
        raise NotImplementedError

    def model_evaluation(self, x_test, y_test):
        """ Runs commands to gather all evaluations for later summaries and plots. """
        # Prediction evaluation
        y_pred = self.model.predict(x_test)
        metric_list = class_eval(y_test, y_pred)
        # Determine probabilities of class predictions for each test instance
        # (this will be used much later in calculating an ROC curve)
        probas_ = self.model.predict_proba(x_test)
        # Compute ROC curve and area the curve
        fpr, tpr, thresholds = metrics.roc_curve(y_test, probas_[:, 1])
        roc_auc = auc(fpr, tpr)
        # Compute Precision/Recall curve and AUC
        prec, recall, thresholds = metrics.precision_recall_curve(y_test, probas_[:, 1])
        prec, recall, thresholds = prec[::-1], recall[::-1], thresholds[::-1]
        prec_rec_auc = auc(recall, prec)
        ave_prec = metrics.average_precision_score(y_test, probas_[:, 1])
        return metric_list, fpr, tpr, roc_auc, prec, recall, prec_rec_auc, ave_prec, probas_

    def fit(self, x_train, y_train, n_trails, timeout):
        self.optimize(x_train, y_train, n_trails, timeout)
        self.model.fit(x_train, y_train)

    def predict(self, x_in):
        self.model.predict(x_in)